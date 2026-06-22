"""
DIA-NN Collection

A collection object for managing multiple DIA-NN search results, following the
same pattern as MSMethodCollection and LCMethodCollection.

Stores searches as combined AnnData objects by level for efficient access and manipulation.
"""

from functools import reduce
import pandas as pd
import anndata as ad
import numpy as np
import zipfile
import tempfile
import shutil
import pickle
from pathlib import Path
from typing import List, Optional, Dict, Tuple
import warnings
import sys
from datetime import datetime
import logging
from .bps_loader import BPSLoader
import zipfile
import os


class BPSCollection:
    """
    Collection object for managing multiple DIA-NN search results.

    Stores searches as combined AnnData objects internally, organized by level.
    Each level contains all samples concatenated together.
    """

    def __init__(self, search_type: str = 'bps_diann', config_path: Optional[str] = None, log_file: Optional[str] = None):
        """
        Initialize BPS collection.

        Parameters:
        -----------
        config_path : str
            Path to YAML configuration file defining column mappings
        log_file : str, optional
            Path to log file. If provided, all print output will be written to this file.
            If None, output goes to stdout only.
        """
        self.search_type = search_type

        if config_path is None:
            if "diann" in search_type: 
                config_path = "diann_columns.yaml"
            elif 'spectronaut' in search_type:
                config_path = "spnt_columns.yaml"
            else:
                config_path = "diann_columns.yaml"

        if not os.path.isabs(config_path):
            module_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(module_dir, config_path)

        self.loader = BPSLoader(search_type=search_type, config_path=config_path)
        # Store as dict: {level: AnnData} where each AnnData contains all samples
        self.data: Dict[str, ad.AnnData] = {}
        self.temp_dirs: List[str] = []

        # Set up logging
        self.log_file = log_file
        self.log_handle = None
        if log_file:
            self.log_handle = open(log_file, 'w')
            self._log(f"DiannCollection Log - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self._log("=" * 80)

            # Configure Python logging to write to log file
            # Set up handler for both this module and anndiannloader
            log_handler = logging.StreamHandler(self.log_handle)
            log_handler.setLevel(logging.INFO)
            formatter = logging.Formatter('%(message)s')
            log_handler.setFormatter(formatter)

            # Configure anndiannloader logger
            anndiann_logger = logging.getLogger('anndiannloader')
            anndiann_logger.setLevel(logging.INFO)
            anndiann_logger.addHandler(log_handler)
            anndiann_logger.propagate = False  # Don't propagate to root logger

            # Redirect warnings to logging
            logging.captureWarnings(True)
            warnings_logger = logging.getLogger('py.warnings')
            warnings_logger.addHandler(log_handler)
            warnings_logger.propagate = False

    
    def _log(self, message: str, to_stdout: Optional[bool] = None):
        """
        Log a message to log file and optionally stdout.

        Parameters:
        -----------
        message : str
            Message to log
        to_stdout : bool, optional
            Whether to also print to stdout. If None (default), prints to stdout
            only when no log file is configured. When log file is configured,
            output goes only to the log file.
        """
        # If to_stdout is not specified, default based on whether log file is configured
        if to_stdout is None:
            to_stdout = self.log_handle is None  # Only print to stdout if no log file

        if to_stdout:
            print(message)

        if self.log_handle:
            self.log_handle.write(message + '\n')
            self.log_handle.flush()

    def close_log(self):
        """Close the log file if it's open."""
        if self.log_handle:
            self._log("\n" + "=" * 80)
            self._log(f"Log closed - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            # Remove logging handlers
            anndiann_logger = logging.getLogger('anndiannloader')
            for handler in anndiann_logger.handlers[:]:
                handler.close()
                anndiann_logger.removeHandler(handler)

            warnings_logger = logging.getLogger('py.warnings')
            for handler in warnings_logger.handlers[:]:
                handler.close()
                warnings_logger.removeHandler(handler)

            self.log_handle.close()
            self.log_handle = None

    def _load_bps_diann_export(self, bps_export_path_obj, target_uuids=None, verbose=False):
        results = {}

        with zipfile.ZipFile(bps_export_path_obj, 'r') as export_zip:
            # Get all entries in the zip file
            all_paths = export_zip.namelist()
            all_result_zips = [i for i in all_paths if 'tims-diann.result.zip' in i]
            if verbose:
                print(f"Found {len(all_result_zips)} tims-diann.result.zip files")

            for result_zip_path in all_result_zips:
                try:
                    # Extract the tims-diann.result.zip to a temporary location
                    with tempfile.TemporaryDirectory() as temp_dir:
                        # Extract the inner zip file to temp directory
                        inner_zip_path = export_zip.extract(result_zip_path, temp_dir)
                        # Open the extracted inner zip file
                        with zipfile.ZipFile(inner_zip_path, 'r') as inner_zip:
                            # Check if results.tsv exists in the inner zip
                            if 'results.tsv' in inner_zip.namelist():
                                uuid = result_zip_path.split('/')[1]
                                if target_uuids is None or uuid in target_uuids:
                                    tsv_path = inner_zip.extract('results.tsv', temp_dir)
                                    # Read the data immediately while temp dir exists
                                    df = pd.read_csv(tsv_path, sep='\t')
                                    # df['source_zip'] = result_zip_path  # Add source info
                                    results[uuid] = df
                except Exception as e:
                    if verbose:
                        print(f"  Error processing {result_zip_path}: {e}")
        return results

    def _load_fragpipe_diann(self, fragpipe_path):
        reports = fragpipe_path.rglob('**/report.tsv')
        return {report.parent.parent.name: pd.read_csv(report, sep='\t') for report in reports}

    def _find_results_files(
        self,
        path: str,
        metadata: Optional[pd.DataFrame] = None,
        levels: Optional[List[str]] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Load and return results data using helper functions for different search types.
        
        Parameters:
        -----------
        path : str
            Path to search results
        metadata : pd.DataFrame, optional
            Metadata for filtering specific searches
        levels : List[str], optional
            Specific levels to load (for Spectronaut: peptide, protein)
            If None, loads all available levels
        
        Returns:
        --------
        Dict[str, pd.DataFrame]
            Dictionary mapping sample names to their data DataFrames
        """
        
        p = Path(path)
        results_data = {}
        
        # Extract target UUIDs if metadata is provided
        target_uuids = None
        if metadata is not None and 'processing_run_uuid' in metadata.columns:
            target_uuids = set(metadata['processing_run_uuid'].dropna().unique())
            self._log(f"Filtering for {len(target_uuids)} specific searches from metadata")

        if self.search_type == 'bps_diann':
            if p.is_dir():
                # Process direct TSV files
                tsv_files = list(p.rglob("results.tsv"))
                for tsv in tsv_files:
                    # Extract sample name from path structure
                    path_parts = tsv.parts
                    sample_name = None
                    for i, part in enumerate(path_parts):
                        if part == 'processing-run' and i + 1 < len(path_parts):
                            sample_name = path_parts[i + 1]
                            break
                    
                    # Fallback to parent directory name if no processing-run found
                    if sample_name is None:
                        sample_name = tsv.parent.name
                        if sample_name.endswith('.results.tsv'):
                            sample_name = sample_name[:-12]

                    # Filter by metadata if provided
                    if target_uuids is not None and sample_name not in target_uuids:
                        continue
                    
                    # Load the TSV file directly
                    try:
                        df = pd.read_csv(tsv, sep='\t')
                        results_data[sample_name] = df
                    except Exception as e:
                        self._log(f"Error reading {tsv}: {e}")
                        continue
                    
                # Process zip files using _load_bps_diann_export
                for zip_file in p.rglob("*.zip"):
                    try:
                        if zipfile.is_zipfile(zip_file):
                            bps_results = self._load_bps_diann_export(zip_file, target_uuids)
                            results_data.update(bps_results)
                    except Exception as e:
                        self._log(f"Error processing BPS zip {zip_file}: {e}")
                        continue

            elif zipfile.is_zipfile(p):
                # Single zip file - use _load_bps_diann_export
                try:
                    bps_results = self._load_bps_diann_export(p, target_uuids)
                    results_data.update(bps_results)
                except Exception as e:
                    self._log(f"Error processing BPS zip {p}: {e}")

        elif 'fragpipe_diann' in self.search_type:
            if p.is_dir():
                # Use _load_fragpipe_diann for directory
                try:
                    fragpipe_results = self._load_fragpipe_diann(p)
                    
                    # # Filter by metadata if provided
                    # if target_uuids is not None:
                    #     fragpipe_results = {
                    #         k: v for k, v in fragpipe_results.items() 
                    #         if k in target_uuids
                    #     }
                    results_data.update(fragpipe_results)
                except Exception as e:
                    self._log(f"Error processing FragPipe directory {p}: {e}")

            elif zipfile.is_zipfile(p):
                # Extract zip and then use _load_fragpipe_diann
                try:
                    temp_dir = tempfile.mkdtemp(prefix='fragpipe_extract_')
                    self.temp_dirs.append(temp_dir)

                    with zipfile.ZipFile(p, 'r') as zf:
                        zf.extractall(temp_dir)

                    fragpipe_results = self._load_fragpipe_diann(Path(temp_dir))
                    
                    # Filter by metadata if provided
                    if target_uuids is not None:
                        fragpipe_results = {
                            k: v for k, v in fragpipe_results.items() 
                            if k in target_uuids
                        }
                    
                    results_data.update(fragpipe_results)
                    
                except Exception as e:
                    self._log(f"Error processing FragPipe zip {p}: {e}")

        elif self.search_type == 'bps_spectronaut':
            if levels is not None:
                self._log(f"Filtering Spectronaut files for levels: {levels}")
            
            if p.is_dir():
                # Look specifically for spectronaut-id.peptide.parquet and spectronaut-id.protein.parquet
                # Filter based on requested levels for efficiency
                spectronaut_files = []
                if levels is None or 'peptide' in levels:
                    peptide_files = list(p.rglob("spectronaut-id.peptide.parquet"))
                    spectronaut_files.extend(peptide_files)
                    if peptide_files:
                        self._log(f"Found {len(peptide_files)} peptide parquet files")
                if levels is None or 'protein' in levels:
                    protein_files = list(p.rglob("spectronaut-id.protein.parquet"))
                    spectronaut_files.extend(protein_files)
                    if protein_files:
                        self._log(f"Found {len(protein_files)} protein parquet files")
                
                for parquet_file in spectronaut_files:
                    # Extract sample name from the parent directory containing the parquet file
                    # Typically this would be something like processing-runs/uuid/p8s/
                    path_parts = parquet_file.parts
                    sample_name = None
                    
                    # Look for processing-runs pattern
                    for i, part in enumerate(path_parts):
                        if 'processing-run' in part and i + 1 < len(path_parts):
                            sample_name = path_parts[i + 1]
                            break
                    
                    # Fallback to parent directory name if no processing-run found
                    if sample_name is None:
                        sample_name = parquet_file.parent.parent.name  # Go up to get meaningful name
                    
                    # Add level info to distinguish peptide vs protein files
                    file_type = 'peptide' if 'peptide' in parquet_file.name else 'protein'
                    sample_key = f"{sample_name}_{file_type}"

                    # Filter by metadata if provided
                    if target_uuids is not None and sample_name not in target_uuids:
                        continue

                    # Load the Parquet file directly
                    try:
                        df = pd.read_parquet(parquet_file)
                        df['file_type'] = file_type  # Add metadata about file type
                        results_data[sample_key] = df
                        self._log(f"Loaded {file_type} data from {parquet_file.name}")
                    except Exception as e:
                        self._log(f"Error reading {parquet_file}: {e}")
                        continue

            elif zipfile.is_zipfile(p):
                # Handle zipped spectronaut exports
                try:
                    temp_dir = tempfile.mkdtemp(prefix='spectronaut_extract_')
                    self.temp_dirs.append(temp_dir)

                    with zipfile.ZipFile(p, 'r') as zf:
                        # Look for spectronaut files in the zip, filtered by requested levels
                        spectronaut_files = []
                        all_files = zf.namelist()
                        
                        if levels is None or 'peptide' in levels:
                            peptide_files = [name for name in all_files if name.endswith('spectronaut-id.peptide.parquet')]
                            spectronaut_files.extend(peptide_files)
                            if peptide_files:
                                self._log(f"Found {len(peptide_files)} peptide parquet files in zip")
                        if levels is None or 'protein' in levels:
                            protein_files = [name for name in all_files if name.endswith('spectronaut-id.protein.parquet')]
                            spectronaut_files.extend(protein_files)
                            if protein_files:
                                self._log(f"Found {len(protein_files)} protein parquet files in zip")
                        
                        for file_path in spectronaut_files:
                            # Extract the specific file
                            extracted_path = zf.extract(file_path, temp_dir)
                            
                            # Extract sample name from path within zip
                            path_parts = Path(file_path).parts
                            sample_name = None
                            
                            for i, part in enumerate(path_parts):
                                if 'processing-run' in part and i + 1 < len(path_parts):
                                    sample_name = path_parts[i + 1]
                                    break
                            
                            if sample_name is None:
                                sample_name = Path(file_path).parent.parent.name
                            
                            # Add level info to distinguish peptide vs protein files
                            file_type = 'peptide' if 'peptide' in Path(file_path).name else 'protein'
                            sample_key = f"{sample_name}_{file_type}"

                            # Filter by metadata if provided
                            if target_uuids is not None and sample_name not in target_uuids:
                                continue
                            
                            # Load the extracted Parquet file
                            try:
                                df = pd.read_parquet(extracted_path)
                                df['file_type'] = file_type  # Add metadata about file type
                                results_data[sample_key] = df
                                self._log(f"Loaded {file_type} data from zip: {file_path}")
                            except Exception as e:
                                self._log(f"Error reading {file_path} from zip: {e}")
                                continue
                                
                except Exception as e:
                    self._log(f"Error processing Spectronaut zip {p}: {e}")

        else:
            raise ValueError(f"Unknown search_type: {self.search_type}. Must be 'bps_diann', 'bps_spectronaut', or 'fragpipe_diann'")
        
        # Report summary of what was found
        if results_data:
            if 'bps' in self.search_type:
                print(1)
                self._log(f"\n📊 Summary: Found {len(results_data)} total samples")
                self._log(f"   UUIDs/samples: {list(results_data.keys())}")
            elif 'fragpipe_diann' in self.search_type:
                self._log(f"\n📊 Summary: Found {len(results_data.keys())} FragPipe-DIA-NN report.tsv")
                self._log(f"   Samples: {np.sum([len(results_data[n]['File.Name'].unique()) for n in results_data.keys()])}")
        else:
            self._log(f"\n⚠ No data found for search_type '{self.search_type}'")
                    
        return results_data

    def _get_search_path(self, path: str) -> str:
        """
        Process and validate search path.
        
        Parameters:
        -----------
        path : str
            Input path
            
        Returns:
        --------
        str
            Processed path
        """
        return str(Path(path).resolve())

    def add_searches(
        self,
        path: str | list,
        levels: Optional[List[str]] = None,
        sections: Optional[List[str]] = None,
        strict: bool = False,
        metadata: Optional[pd.DataFrame] = None,
        verbose: bool = False
    ):
        """
        Load search results from a folder or zip and add to collection.

        Parameters:
        -----------
        path : str | list
            Path to folder or zip file containing search results, or a list of such paths    
        levels : List[str], optional
            Specific levels to load (precursor, protein, gene, peptide)
            If None, loads all available levels
        sections : List[str], optional
            Specific sections to include
        strict : bool
            If True, raise error if expected columns are missing
        metadata : pd.DataFrame, optional
            Metadata dataframe with 'processing_run_uuid' column to filter specific searches.
            If provided, only loads search results matching the UUIDs in the metadata.
            This allows loading only specific searches from large zip files instead of 
            extracting everything.
        """
        # Convert single path to list for uniform handling
        paths = path if isinstance(path, list) else [path]
        
        # Get target UUIDs if metadata is provided
        target_uuids = None
        if metadata is not None and 'processing_run_uuid' in metadata.columns:
            target_uuids = set(metadata['processing_run_uuid'].dropna().unique())
        
        all_results_data = {}
        for p in paths:
            search_path = self._get_search_path(p)
            results_data = self._find_results_files(search_path, metadata=metadata, levels=levels)
            all_results_data.update(results_data)

        if not all_results_data:
            expected_structure = {
                'bps_diann': 'tims-diann.result/results.tsv',
                'bps_spectronaut': 'spectronaut-id.peptide.parquet / spectronaut-id.protein.parquet',
                'fragpipe': 'sample/diann-output/report.tsv'
            }
            self._log(f"⚠ No results found in {len(paths)} path(s) for search_type='{self.search_type}'", to_stdout=verbose)
            self._log(f"  Expected structure: {expected_structure.get(self.search_type, 'unknown')}", to_stdout=verbose)
            self._log(f"  Continuing with empty collection...", to_stdout=verbose)
            return

        self._log(f"Found {len(all_results_data)} result samples ({self.search_type} format)", to_stdout=verbose)
        
        # Log which UUIDs were found if metadata filtering was used
        if target_uuids is not None:
            found_uuids = set(all_results_data.keys())
            missing_uuids = target_uuids - found_uuids
            if found_uuids:
                self._log(f"Successfully found {len(found_uuids)} searches from metadata", to_stdout=verbose)
            if missing_uuids:
                self._log(f"Warning: {len(missing_uuids)} searches from metadata not found: {missing_uuids}", to_stdout=verbose)

        # Determine which levels to load
        if levels is None:
            levels = list(self.loader.config['levels'].keys())

        # Temporary storage for sample AnnData objects before concatenation
        level_samples: Dict[str, List[ad.AnnData]] = {level: [] for level in levels}

        # Process each results dataframe
        for uuid, results_df in all_results_data.items():
            self._log(f"\nProcessing {uuid}", to_stdout=verbose)
            
            # For Spectronaut data, process DataFrame directly without TSV conversion
            if 'spectronaut' in self.search_type:
                # Extract the level type from the UUID (peptide or protein)
                level_type = 'peptide' if '_peptide' in uuid else 'protein'
                
                # Only process if this level is requested
                if level_type not in levels:
                    continue
                    
                try:
                    self._log(f"  Loading {level_type} level...", to_stdout=verbose)
                    
                    # Add to temporary list for concatenation (like other search types)
                    level_samples[level_type].append(results_df)
                    
                    self._log(f"    ✓ {level_type}: {results_df.shape}", to_stdout=verbose)
                    
                except Exception as e:
                    if not strict:
                        self._log(f"⚠ Could not load {level_type} level: \n{e}", to_stdout=verbose)
                    else:
                        self._log(f"Error loading {uuid} at {level_type} level: {e}", to_stdout=verbose)
                    continue
                    
            else:
                # For DIA-NN data, use the original TSV-based approach
                temp_path = None
                try:
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.tsv', delete=False) as temp_file:
                        results_df.to_csv(temp_file.name, sep='\t', index=False)
                        temp_path = temp_file.name
                    
                    # Check which levels are available FIRST (more efficient - only reads header)
                    available_levels = self.loader.check_available_levels(
                        temp_path,
                        sections=sections
                    )

                    # Try to load each requested level
                    for level in levels:
                        level_info = available_levels.get(level, {})

                        try:
                            self._log(f"  Loading {level} level...", to_stdout=verbose)

                            # Load using the temporary file path
                            df = self.loader.load_to_df(
                                temp_path,
                                level=level,
                                sections=sections,
                                strict=False
                            )

                            # Add sample UUID/name to df (only for non-Spectronaut data)
                            if 'spectronaut' not in self.search_type:
                                df['UUID'] = uuid

                            # Add to temporary list for concatenation
                            level_samples[level].append(df)

                            # Print DataFrame summary
                            self._log(f"    ✓ {level}: {df.shape}", to_stdout=verbose)

                        except Exception as e:
                            # Handle errors during loading
                            if not strict:
                                self._log(f"⚠ Could not load {level} level: \n{e}", to_stdout=verbose)
                            else:
                                self._log(f"Error loading {uuid} at {level} level: {e}", to_stdout=verbose)
                                break
                            continue
                            
                except Exception as e:
                    self._log(f"⚠ Error processing {uuid}: {e}")
                finally:
                    # Clean up temp file
                    if temp_path:
                        try:
                            os.unlink(temp_path)
                        except:
                            pass
        # Concatenate samples for each level (for all search types)
        self._log("\nCombining samples across levels...", to_stdout=verbose)

        for level in levels:
            if level_samples[level]:  # If we have any samples for this level
                self._log(f"  Combining {len(level_samples[level])} samples for {level} level...", to_stdout=verbose)

                # Concatenate DataFrames first, then convert to AnnData
                concat_df = pd.concat(level_samples[level], axis=0, ignore_index=True)

                adata = self.loader.load_to_adata(
                            concat_df,
                            level=level,
                            sections=sections,
                            strict=False
                    )

                # If level already exists in collection, concatenate with existing data
                if level in self.data:
                    self._log(f"    Concatenating with existing {level} data...")
                    existing = self.data[level]

                    # adata concat with merge "first" fills in na values in the obs when concating the var
                    # need to perform separate obs merge to ensure we keep all obs metadata from both existing and new data, and then reassign to adata.obs after the var concat

                    # merged_obs = existing.obs.merge(adata.obs, how='outer', left_index=True, right_index=True)
                    merged_obs = pd.concat([existing.obs, adata.obs], axis=0).drop_duplicates()

                    adata = ad.concat(
                        [existing, adata],
                        axis=1,  # Concatenate along var (columns/samples) axis
                        join='outer',
                        merge=None  # Keep first value for non-aligned obs metadata
                    )
                    
                    merged_obs.reindex(index=adata.obs_names, fill_value=np.nan)
                    adata.obs = merged_obs
                    adata.obs_names = merged_obs.index
                    
                    self.data[level] = adata
                    self._log(f"    ✓ Concatenated {level} with shape: {self.data[level].shape}")
                else:
                    # First time adding this level
                    self.data[level] = adata
                    self._log(f"    ✓ Added new {level} level with shape: {self.data[level].shape}")


    def get(self, level: str, sample: Optional[str] = None) -> ad.AnnData:
        """
        Get AnnData object for a specific level, optionally filtered by sample.

        Parameters:
        -----------
        level : str
            Analysis level (precursor, protein, gene)
        sample : str, optional
            If provided, return only data for this sample

        Returns:
        --------
        ad.AnnData
            AnnData object for the level (all samples or filtered)
        """
        if level not in self.data:
            raise KeyError(f"Level '{level}' not found. Available levels: {list(self.data.keys())}")

        adata = self.data[level]

        if sample is not None:
            # Filter to specific sample (select columns)
            if 'Sample' not in adata.var.columns:
                raise KeyError("Sample column not found in var DataFrame")
            mask = adata.var_names == sample
            if mask.sum() == 0:
                raise ValueError(f"Sample '{sample}' not found in level '{level}'")
            return adata[:, mask].copy()  # Select columns, not rows

        return adata

    def list_samples(self, level: Optional[str] = None) -> List[str]:
        """
        List all sample names in collection.

        Parameters:
        -----------
        level : str, optional
            If provided, return samples for this level only

        Returns:
        --------
        List[str]
            Sample names
        """
        if level is not None:
            if level not in self.data:
                return []
            return sorted(self.data[level].var_names.unique().tolist())
        else:
            # Return union of all samples across all levels
            all_samples = set()
            for adata in self.data.values():
                if 'Sample' in adata.var.columns:
                    all_samples.update(adata.var_names.unique())
            return sorted(list(all_samples))

    def list_levels(self) -> List[str]:
        """
        List all levels in collection.

        Returns:
        --------
        List[str]
            Level names
        """
        return list(self.data.keys())

    def to_df(
        self,
        level: str,
        samples: Optional[List[str]] = None,
        merge_method: str = 'concat'
    ) -> pd.DataFrame:
        """
        Convert stored AnnData object to DataFrame.

        Parameters:
        -----------
        level : str
            Analysis level
        samples : List[str], optional
            Specific samples to include (if None, includes all)
        merge_method : str
            How to format output ('concat' for long format, others TBD)

        Returns:
        --------
        pd.DataFrame
            DataFrame with data
        """
        adata = self.get(level)

        if samples is not None:
            # Filter to specific samples (select columns)
            mask = adata.var_names.isin(samples)
            adata = adata[:, mask].copy()

        # Convert to DataFrame (long format)
        # This creates a melted format with genes × samples
        df_list = []
        for i, sample in enumerate(adata.var_names):
            sample_df = adata.obs.copy()
            sample_df['Sample'] = sample
            sample_df['X'] = adata.X[:, i]
            df_list.append(sample_df)

        return pd.concat(df_list, ignore_index=True) if df_list else pd.DataFrame()

    def summary_df(self) -> pd.DataFrame:
        """
        Create summary DataFrame showing samples and their data shapes per level.

        Returns:
        --------
        pd.DataFrame
            Summary with sample counts and shapes for each level
        """
        summary_data = []

        for level, adata in self.data.items():
            if 'Sample' in adata.var.columns:
                samples = adata.var_names.unique()
                for sample in samples:
                    # Each sample is a column, so n_obs is constant across samples
                    summary_data.append({
                        'Sample': sample,
                        'Level': level,
                        'n_obs': adata.n_obs,  # Number of genes/proteins/precursors
                        'n_vars': 1,  # Each sample is one column
                        'shape': f"({adata.n_obs}, {adata.n_vars})"
                    })

        if not summary_data:
            return pd.DataFrame()

        df = pd.DataFrame(summary_data)

        # Pivot to have one row per sample with columns for each level
        pivot = df.pivot(index='Sample', columns='Level', values=['n_obs', 'n_vars', 'shape'])
        pivot.columns = [f'{level}_{stat}' for stat, level in pivot.columns]
        pivot = pivot.reset_index()

        return pivot

    def save(self, filepath: str):
        """
        Save collection to file.

        Parameters:
        -----------
        filepath : str
            Path to save file (.pkl or .h5ad)
        """
        filepath_obj = Path(filepath)

        if filepath_obj.suffix == '.pkl':
            # Save as pickle
            with open(filepath_obj, 'wb') as f:
                pickle.dump(self.data, f)
            self._log(f"Saved collection to {filepath_obj}")

        elif filepath_obj.suffix == '.h5ad':
            # Save each level as separate h5ad file in a directory
            filepath_obj.mkdir(parents=True, exist_ok=True)
            for level, adata in self.data.items():
                level_path = filepath_obj / f"{level}.h5ad"
                adata.write_h5ad(level_path)
            self._log(f"Saved collection to {filepath_obj} (directory with {len(self.data)} level files)")

        else:
            raise ValueError(f"Unsupported file format: {filepath_obj.suffix}. Use .pkl or .h5ad")

    @classmethod
    def from_file(cls, filepath: str, search_type: str = "bps_diann", config_path: Optional[str] = None) -> 'BPSCollection':
        """
        Load collection from file.

        Parameters:
        -----------
        filepath : str
            Path to saved file
        search_type : str
            Type of search (default: "bps_spectronaut")
        config_path : str
            Path to YAML configuration file

        Returns:
        --------
        BPSCollection
            Loaded collection
        """

        if config_path is None:
            if "diann" in search_type: 
                config_path = "diann_columns.yaml"
            elif 'spectronaut' in search_type:
                config_path = "spnt_columns.yaml"
            else:
                config_path = "diann_columns.yaml"
                
        filepath_obj = Path(filepath)
        collection = cls(config_path)

        if filepath_obj.suffix == '.pkl':
            # Load from pickle
            with open(filepath_obj, 'rb') as f:
                collection.data = pickle.load(f)
            collection._log(f"Loaded collection from {filepath_obj}")

        elif filepath_obj.suffix == '.h5ad' or filepath_obj.is_dir():
            # Load from h5ad directory
            if not filepath_obj.is_dir():
                raise ValueError(f"For .h5ad format, path must be a directory: {filepath_obj}")

            for level_file in filepath_obj.glob("*.h5ad"):
                level = level_file.stem
                collection.data[level] = ad.read_h5ad(level_file)
            collection._log(f"Loaded collection from {filepath_obj} ({len(collection.data)} levels)")

        else:
            raise ValueError(f"Unsupported file format: {filepath_obj.suffix}. Use .pkl or .h5ad")

        return collection

    def __getitem__(self, key: str) -> ad.AnnData:
        """
        Get AnnData by level name.

        Parameters:
        -----------
        key : str
            Level name

        Returns:
        --------
        ad.AnnData
            Combined AnnData object for the level
        """
        return self.get(key)

    def __contains__(self, key: str) -> bool:
        """Check if level exists in collection."""
        return key in self.data

    def __len__(self) -> int:
        """Return number of unique samples across all levels."""
        return len(self.list_samples())

    def __repr__(self) -> str:
        """String representation of collection."""
        levels = list(self.data.keys())
        return f"BPSCollection(levels={levels})"

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup temp directories and close log file."""
        for temp_dir in self.temp_dirs:
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass

        # Close log file if open
        if self.log_handle:
            self._log("\n" + "=" * 80)
            self._log(f"Log closed - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.log_handle.close()
            self.log_handle = None

        return False
