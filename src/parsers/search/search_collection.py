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
from .search_loader import SearchLoader
import zipfile
from typing import List, Optional, Dict, Union
import os


class SearchCollection:
    """
    Collection object for managing multiple DIA-NN search results.

    Stores searches as combined AnnData objects internally, organized by level.
    Each level contains all samples concatenated together.
    """

    def __init__(self, container: str = 'bps', engine: str = 'diann', config_path: Optional[str] = None, log_file: Optional[str] = None, additional_columns: Optional[Dict[str, Dict]] = None, search_type: Optional[str] = None):
        """
        Initialize SearchCollection.

        Parameters:
        -----------
        container : str
            Data container type ('bps', 'fragpipe', 'diann')
        engine : str
            Search engine type ('diann', 'spectronaut')
        config_path : str
            Path to YAML configuration file defining column mappings
        log_file : str, optional
            Path to log file. If provided, all print output will be written to this file.
            If None, output goes to stdout only.
        additional_columns : Dict[str, Dict], optional
            Dictionary mapping custom column names to their configuration.
            See SearchLoader documentation for format.
        search_type : str, optional
            DEPRECATED: Use container and engine parameters instead.
            Format: 'container_engine' (e.g., 'bps_diann')
        """
        # Handle deprecated search_type parameter
        if search_type is not None:
            warnings.warn(
                "The 'search_type' parameter is deprecated. Use 'container' and 'engine' parameters instead.",
                DeprecationWarning,
                stacklevel=2
            )
            parts = search_type.split('_')
            if len(parts) == 2:
                container, engine = parts
            elif len(parts) == 1:
                # Handle single values like 'diann'
                if parts[0] in ['diann', 'spectronaut']:
                    engine = parts[0]
                    container = 'diann' if engine == 'diann' else 'bps'
                else:
                    container = parts[0]
                    engine = 'diann'
        
        self.container = container
        self.engine = engine
        
        # Maintain search_type as a computed property for backward compatibility
        self.search_type = f"{container}_{engine}"

        if config_path is None:
            if engine == 'diann': 
                config_path = "diann_columns.yaml"
            elif engine == 'spectronaut':
                config_path = "spnt_columns.yaml"
            else:
                config_path = "diann_columns.yaml"

        if not os.path.isabs(config_path):
            module_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(module_dir, config_path)

        self.loader = SearchLoader(container=container, engine=engine, config_path=config_path, additional_columns=additional_columns)
        # Store as dict: {level: AnnData} where each AnnData contains all samples
        self.data: Dict[str, ad.AnnData] = {}
        self.temp_dirs: List[str] = []
        self.search_index: Dict[str, int] = {}
        
        # Track pending column configurations that haven't been committed to loader yet
        self.pending_column_configs: Dict[str, Dict] = {}

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

    def _load_bps_diann_export(self, search_export_path_obj, target_uuids=None, verbose=False):
        results = {}
        
        # Get absolute path to the export zip
        export_zip_abs = os.path.abspath(str(search_export_path_obj))
        
        if verbose:
            self._log(f"Opening export zip: {export_zip_abs}", to_stdout=True)

        with zipfile.ZipFile(search_export_path_obj, 'r') as export_zip:
            # Get all entries in the zip file
            all_paths = export_zip.namelist()
            all_result_zips = [i for i in all_paths if 'tims-diann.result.zip' in i]
            if verbose:
                self._log(f"Found {len(all_result_zips)} tims-diann.result.zip files", to_stdout=True)
                for path in all_result_zips:
                    self._log(f"  - {path}", to_stdout=True)

            for result_zip_path in all_result_zips:
                try:
                    # Extract the tims-diann.result.zip to a temporary location
                    with tempfile.TemporaryDirectory() as temp_dir:
                        # Extract the inner zip file to temp directory
                        inner_zip_path = export_zip.extract(result_zip_path, temp_dir)
                        if verbose:
                            self._log(f"Extracting: {result_zip_path}", to_stdout=True)
                        # Open the extracted inner zip file
                        with zipfile.ZipFile(inner_zip_path, 'r') as inner_zip:
                            # Check if results.tsv exists in the inner zip
                            if 'results.tsv' in inner_zip.namelist():
                                uuid = result_zip_path.split('/')[1]
                                if target_uuids is None or uuid in target_uuids:
                                    tsv_path = inner_zip.extract('results.tsv', temp_dir)
                                    # Read the data immediately while temp dir exists
                                    df = pd.read_csv(tsv_path, sep='\t')
                                    # Store the absolute path to the export zip for tracking
                                    # Format: /absolute/path/to/export.zip::uuid/tims-diann.result.zip
                                    df['_source_zip'] = export_zip_abs + '::' + result_zip_path
                                    results[uuid] = df
                                    if verbose:
                                        self._log(f"  ✓ Loaded UUID {uuid}: {df.shape}", to_stdout=True)
                                elif verbose:
                                    self._log(f"  ⊘ Skipped UUID {uuid} (not in target list)", to_stdout=True)
                            else:
                                if verbose:
                                    self._log(f"  ⚠ No results.tsv in {result_zip_path}", to_stdout=True)
                except Exception as e:
                    if verbose:
                        self._log(f"  ✗ Error processing {result_zip_path}: {e}", to_stdout=True)
                    import traceback
                    if verbose:
                        self._log(traceback.format_exc(), to_stdout=True)
        return results

    def _load_fragpipe_diann(self, fragpipe_path):
        reports = fragpipe_path.rglob('**/report.tsv')
        results = {}
        for report in reports:
            df = pd.read_csv(report, sep='\t')
            # Store absolute path to the report file
            df['_source_zip'] = str(report.resolve())
            results[report] = df
        return results

    def _load_diann_reports(self, diann_path):
        """Load DIA-NN report files (parquet or tsv) from extracted directory."""
        # Look for both parquet and tsv formats
        parquet_reports = list(diann_path.rglob('**/report.parquet'))
        tsv_reports = list(diann_path.rglob('**/report.tsv'))
        reports = parquet_reports + tsv_reports
        
        results = {}
        for report in reports:
            if report.suffix == '.parquet':
                df = pd.read_parquet(report)
            else:  # .tsv
                df = pd.read_csv(report, sep='\t')
            # Store absolute path to the report file
            df['_source_zip'] = str(report.resolve())
            results[report] = df
        return results

    def _find_result_file_paths_single(
        self,
        path: str,
        metadata: Optional[pd.DataFrame] = None,
        levels: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """
        Find result file paths from a single directory or zip file.
        
        Parameters:
        -----------
        path: str
            Path to search results (directory or zip)
        metadata : pd.DataFrame, optional
            Metadata for filtering specific searches
        levels : List[str], optional
            Specific levels to load (for Spectronaut: peptide, protein)
            If None, loads all available levels
        
        Returns:
        --------
        Dict[str, str]
            Dictionary mapping sample IDs to their result file paths
        """
        
        p = Path(path)
        result_file_paths = {}
        
        # Extract target UUIDs if metadata is provided
        target_uuids = None
        if metadata is not None and 'processing_run_uuid' in metadata.columns:
            target_uuids = set(metadata['processing_run_uuid'].dropna().unique())
            self._log(f"Filtering for {len(target_uuids)} specific searches from metadata")

        # If path is a file, try to read it directly
        if p.is_file() and not zipfile.is_zipfile(p):
            # Use filename (without extension) as sample name
            sample_name = p.stem
            result_file_paths[sample_name] = str(p.resolve())
            return result_file_paths

        if self.container == 'bps' and self.engine == 'diann':
            if p.is_dir():
                # Find direct TSV files
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
                    
                    # Store the path
                    result_file_paths[sample_name] = str(tsv.resolve())
                    
                # Find zip files
                for zip_file in p.rglob("*.zip"):
                    if zipfile.is_zipfile(zip_file):
                        result_file_paths[f"zip:{zip_file}"] = str(zip_file.resolve())

            elif zipfile.is_zipfile(p):
                # Single zip file
                result_file_paths[f"zip:{p}"] = str(p.resolve())

        elif self.container == 'fragpipe' and self.engine == 'diann':
            if p.is_dir():
                # Find report.tsv files
                reports = list(p.rglob('**/report.tsv'))
                for report in reports:
                    result_file_paths[str(report)] = str(report.resolve())

            elif zipfile.is_zipfile(p):
                # Store zip path for extraction later
                result_file_paths[f"zip:{p}"] = str(p.resolve())

        elif self.container == 'diann' and self.engine == 'diann':
            if p.is_dir():
                # Find report.parquet or report.tsv files
                reports = list(p.rglob('**/report.parquet')) + list(p.rglob('**/report.tsv'))
                for report in reports:
                    result_file_paths[str(report)] = str(report.resolve())

            elif zipfile.is_zipfile(p):
                # Store zip path for extraction later
                result_file_paths[f"zip:{p}"] = str(p.resolve())

        elif self.container == 'bps' and self.engine == 'spectronaut':
            if levels is not None:
                self._log(f"Filtering Spectronaut files for levels: {levels}")
            
            if p.is_dir():
                # Look specifically for spectronaut parquet files
                spectronaut_files = []
                if levels is None or 'peptide' in levels:
                    peptide_files = list(p.rglob("spectronaut-id.peptide.parquet"))
                    spectronaut_files.extend(peptide_files)
                if levels is None or 'protein' in levels:
                    protein_files = list(p.rglob("spectronaut-id.protein.parquet"))
                    spectronaut_files.extend(protein_files)
                
                for parquet_file in spectronaut_files:
                    # Extract sample name from path
                    path_parts = parquet_file.parts
                    sample_name = None
                    
                    for i, part in enumerate(path_parts):
                        if 'processing-run' in part and i + 1 < len(path_parts):
                            sample_name = path_parts[i + 1]
                            break
                    
                    if sample_name is None:
                        sample_name = parquet_file.parent.parent.name
                    
                    # Add level info to distinguish peptide vs protein files
                    file_type = 'peptide' if 'peptide' in parquet_file.name else 'protein'
                    sample_key = f"{sample_name}_{file_type}"

                    # Filter by metadata if provided
                    if target_uuids is not None and sample_name not in target_uuids:
                        continue

                    result_file_paths[sample_key] = str(parquet_file.resolve())

            elif zipfile.is_zipfile(p):
                # Store zip path for extraction later
                result_file_paths[f"zip:{p}"] = str(p.resolve())

        else:
            raise ValueError(f"Unknown container/engine combination: container='{self.container}', engine='{self.engine}'. Valid combinations: bps+diann, bps+spectronaut, fragpipe+diann, diann+diann")
        
        return result_file_paths

    def _find_all_result_file_paths(
        self,
        paths: str | list,
        metadata: Optional[pd.DataFrame] = None,
        levels: Optional[List[str]] = None,
        verbose: bool = False
    ) -> Dict[str, str]:
        """
        Find all result file paths from multiple directories or zip files.

        Parameters:
        -----------
        paths : str | list
            Path(s) to folder or zip file containing search results
        metadata : pd.DataFrame, optional
            Metadata for filtering specific searches
        levels : List[str], optional
            Specific levels to load
        verbose : bool
            Whether to log verbose output
        
        Returns:
        --------
        Dict[str, str]
            Dictionary mapping sample IDs to their result file paths
        """
        # Convert single path to list for uniform handling
        paths = paths if isinstance(paths, list) else [paths]
        
        all_result_paths = {}
        for p in paths:
            search_path = self._get_search_path(p)
            result_paths = self._find_result_file_paths_single(search_path, metadata=metadata, levels=levels)
            all_result_paths.update(result_paths)

        if not all_result_paths:
            expected_structure = {
                'bps_diann': 'tims-diann.result/results.tsv',
                'bps_spectronaut': 'spectronaut-id.peptide.parquet / spectronaut-id.protein.parquet',
                'fragpipe': 'sample/diann-output/report.tsv'
            }
            self._log(f"⚠ No results found in {len(paths)} path(s) for search_type='{self.search_type}'", to_stdout=verbose)
            self._log(f"  Expected structure: {expected_structure.get(self.search_type, 'unknown')}", to_stdout=verbose)
            return all_result_paths

        self._log(f"Found {len(all_result_paths)} result file paths ({self.search_type} format)", to_stdout=verbose)
        
        return all_result_paths

    def _read_raw_result_file(self, file_path: str, sample_id: str) -> pd.DataFrame:
        """
        Read a single raw result file (TSV or Parquet).
        
        Parameters:
        -----------
        file_path : str
            Path to the result file
        sample_id : str
            Sample identifier (may have 'zip:' prefix for zip files)
        
        Returns:
        --------
        pd.DataFrame
            Raw data from the file
        """
        try:
            # Check if this is a zip file based on the sample_id prefix
            if sample_id.startswith('zip:'):
                # Handle zip files
                if self.container == 'bps' and self.engine == 'diann':
                    self._log(f"Loading BPS DIA-NN export from: {file_path}", to_stdout=True)
                    results = self._load_bps_diann_export(file_path, verbose=True)
                    self._log(f"Found {len(results)} searches in export", to_stdout=True)
                    if not results:
                        self._log("⚠ No searches found in export zip", to_stdout=True)
                        return pd.DataFrame()
                    # Return combined results with source tracking
                    all_dfs = []
                    for uuid, df in results.items():
                        self._log(f"  - {uuid}: {df.shape}", to_stdout=True)
                        all_dfs.append(df)
                    return pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()
                elif self.container == 'fragpipe' and self.engine == 'diann':
                    # Extract and load fragpipe results
                    temp_dir = tempfile.mkdtemp(prefix='fragpipe_extract_')
                    self.temp_dirs.append(temp_dir)
                    with zipfile.ZipFile(file_path, 'r') as zf:
                        zf.extractall(temp_dir)
                    results = self._load_fragpipe_diann(Path(temp_dir))
                    all_dfs = list(results.values())
                    return pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()
                elif self.container == 'diann' and self.engine == 'diann':
                    # Extract and load diann results (report.parquet or report.tsv)
                    temp_dir = tempfile.mkdtemp(prefix='diann_extract_')
                    self.temp_dirs.append(temp_dir)
                    with zipfile.ZipFile(file_path, 'r') as zf:
                        zf.extractall(temp_dir)
                    results = self._load_diann_reports(Path(temp_dir))
                    all_dfs = list(results.values())
                    return pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()
                elif self.engine == 'spectronaut':
                    # Extract and load spectronaut results
                    temp_dir = tempfile.mkdtemp(prefix='spectronaut_extract_')
                    self.temp_dirs.append(temp_dir)
                    with zipfile.ZipFile(file_path, 'r') as zf:
                        zf.extractall(temp_dir)
                    # Find parquet files in extracted directory
                    extracted_path = Path(temp_dir)
                    parquet_files = list(extracted_path.rglob("*.parquet"))
                    if parquet_files:
                        df = pd.read_parquet(parquet_files[0])
                        file_type = 'peptide' if 'peptide' in parquet_files[0].name else 'protein'
                        df['file_type'] = file_type
                        return df
                    return pd.DataFrame()
            elif file_path.endswith('.parquet'):
                # Read parquet file
                df = pd.read_parquet(file_path)
                # Add file type metadata for Spectronaut
                if self.engine == 'spectronaut':
                    file_type = 'peptide' if 'peptide' in file_path else 'protein'
                    df['file_type'] = file_type
                return df
            elif file_path.endswith('.tsv'):
                # Read TSV file
                df = pd.read_csv(file_path, sep='\t')
                df['_source_zip'] = file_path
                return df
            else:
                raise ValueError(f"Unsupported file format: {file_path}")
        except Exception as e:
            self._log(f"Error reading {file_path}: {e}")
            return pd.DataFrame()

    def _load_raw_result_dfs(
        self,
        file_paths: Dict[str, str],
        verbose: bool = False
    ) -> Dict[str, pd.DataFrame]:
        """
        Load raw result files without level-specific transformation.
        
        Parameters:
        -----------
        file_paths : Dict[str, str]
            Dictionary mapping sample IDs to file paths
        verbose : bool
            Whether to log verbose output
        
        Returns:
        --------
        Dict[str, pd.DataFrame]
            Dictionary mapping sample IDs to raw DataFrames
        """
        raw_dfs = {}
        
        for sample_id, file_path in file_paths.items():
            self._log(f"\nLoading {sample_id}", to_stdout=verbose)
            
            # Read raw file
            results_df = self._read_raw_result_file(file_path, sample_id)
            
            if results_df.empty:
                self._log(f"⚠ Empty data for {sample_id}", to_stdout=verbose)
                continue
            
            raw_dfs[sample_id] = results_df
            self._log(f"  ✓ Loaded: {results_df.shape}", to_stdout=verbose)
        
        return raw_dfs

    def add_computed_columns(
        self,
        raw_dfs: Dict[str, pd.DataFrame],
        transformations: List[Dict],
        commit_immediately: bool = False,
        verbose: bool = False
    ) -> Dict[str, pd.DataFrame]:
        """
        Apply transformations to raw DataFrames to add computed columns.
        
        Parameters:
        -----------
        raw_dfs : Dict[str, pd.DataFrame]
            Dictionary mapping sample IDs to raw DataFrames
        transformations : List[Dict]
            List of transformation specifications. Each dict should contain:
            - 'column_name': str - Name of the new column
            - 'function': callable or str - Function to apply or string expression to eval
            - 'storage': str - Where to store in AnnData ('var', 'obs', or 'layer')
            - 'levels': List[str] or None - Which levels to apply to (None = all)
            - 'section': str - Which section (default: 'optional')
        commit_immediately : bool
            If True, commit column configs to loader immediately. If False (default),
            store as pending configs that can be committed later.
        verbose : bool
            Whether to log verbose output
            
        Returns:
        --------
        Dict[str, pd.DataFrame]
            Modified DataFrames with new columns
            
        Examples:
        ---------
        # Using a function
        transformations = [{
            'column_name': 'log_intensity',
            'function': lambda df: np.log10(df['Intensity'] + 1),
            'storage': 'layer',
            'levels': ['precursor'],
            'section': 'quantification'
        }]
        
        # Using a string expression
        transformations = [{
            'column_name': 'intensity_ratio',
            'function': 'df["Intensity"] / df["Precursor.Quantity"]',
            'storage': 'var',
            'levels': None,  # Apply to all levels
            'section': 'optional'
        }]
        """
        if not transformations:
            return raw_dfs
        
        self._log("\nApplying computed column transformations...", to_stdout=verbose)
        
        # Process each transformation
        for transform in transformations:
            column_name = transform['column_name']
            func = transform['function']
            storage = transform.get('storage', 'var')
            levels = transform.get('levels', None)
            section = transform.get('section', 'optional')
            
            # Validate storage type
            if storage not in ['var', 'obs', 'layer']:
                self._log(f"⚠ Invalid storage '{storage}' for column '{column_name}', skipping", to_stdout=verbose)
                continue
            
            # Store column config as pending (don't commit to loader yet)
            self.pending_column_configs[column_name] = {
                'storage': storage,
                'levels': levels,
                'section': section
            }
            
            # Apply transformation to each DataFrame
            applied_count = 0
            for sample_id, df in raw_dfs.items():
                # Determine if transformation should be applied to this sample
                # For Spectronaut, check if sample matches level constraint
                should_apply = True
                if self.engine == 'spectronaut' and levels is not None:
                    # Extract level from sample_id (e.g., "uuid_peptide" -> "peptide")
                    sample_level = 'peptide' if '_peptide' in sample_id else 'protein'
                    should_apply = sample_level in levels
                
                if not should_apply:
                    continue
                
                try:
                    # Apply transformation
                    if callable(func):
                        # Function provided
                        df[column_name] = func(df)
                    elif isinstance(func, str):
                        # String expression to evaluate
                        df[column_name] = eval(func)
                    else:
                        self._log(f"⚠ Invalid function type for '{column_name}', skipping", to_stdout=verbose)
                        continue
                    
                    applied_count += 1
                    
                except Exception as e:
                    self._log(f"⚠ Error applying transformation '{column_name}' to {sample_id}: {e}", to_stdout=verbose)
                    continue
            
            self._log(f"  ✓ Added column '{column_name}' (storage: {storage}) to {applied_count}/{len(raw_dfs)} samples", to_stdout=verbose)
        
        # Optionally commit column configs immediately
        if commit_immediately:
            self.commit_column_configs(verbose=verbose)
        
        return raw_dfs

    def commit_column_configs(self, verbose: bool = False):
        """Commit pending column configurations to the loader.
        
        Parameters:
        -----------
        verbose : bool
            Whether to log verbose output
        """
        if not self.pending_column_configs:
            self._log("No pending column configurations to commit.", to_stdout=verbose)
            return
        
        self._log(f"\nCommitting {len(self.pending_column_configs)} column configurations to loader...", to_stdout=verbose)
        
        for column_name, config in self.pending_column_configs.items():
            self.loader.add_column_config(
                column_name=column_name,
                storage=config['storage'],
                levels=config['levels'],
                section=config['section']
            )
            self._log(f"  ✓ Committed '{column_name}' (storage: {config['storage']})", to_stdout=verbose)
        
        # Clear pending configs after committing
        self.pending_column_configs.clear()
    
    def clear_pending_column_configs(self):
        """Clear all pending column configurations without committing them."""
        self.pending_column_configs.clear()
    
    def list_pending_column_configs(self) -> Dict[str, Dict]:
        """Return a copy of pending column configurations.
        
        Returns:
        --------
        Dict[str, Dict]
            Dictionary mapping column names to their configurations
        """
        return self.pending_column_configs.copy()

    def _transform_raw_dfs_by_level(
        self,
        raw_dfs: Dict[str, pd.DataFrame],
        levels: List[str],
        sections: Optional[List[str]] = None,
        strict: bool = False,
        verbose: bool = False
    ) -> Dict[str, List[pd.DataFrame]]:
        """
        Transform raw result DataFrames into level-specific DataFrames.
        For Spectronaut, raw files are already level-specific.
        For DIA-NN, raw files contain all levels mixed and need to be split.
        
        Parameters:
        -----------
        raw_dfs : Dict[str, pd.DataFrame]
            Dictionary mapping sample IDs to raw DataFrames
        levels : List[str]
            Levels to extract (precursor, protein, gene, peptide)
        sections : List[str], optional
            Specific sections to include
        strict : bool
            If True, raise error if expected columns are missing
        verbose : bool
            Whether to log verbose output
        
        Returns:
        --------
        Dict[str, List[pd.DataFrame]]
            Dictionary mapping levels to lists of DataFrames
        """
        # Initialize storage for each level
        level_dfs: Dict[str, List[pd.DataFrame]] = {level: [] for level in levels}
        
        for sample_id, results_df in raw_dfs.items():
            self._log(f"\nTransforming {sample_id} by level", to_stdout=verbose)
            
            # For Spectronaut data, DataFrame is already at the correct level
            if self.engine == 'spectronaut':
                level_type = 'peptide' if '_peptide' in sample_id else 'protein'
                
                if level_type not in levels:
                    continue
                    
                try:
                    self._log(f"  {level_type} level...", to_stdout=verbose)
                    level_dfs[level_type].append(results_df)
                    self._log(f"    ✓ {level_type}: {results_df.shape}", to_stdout=verbose)
                except Exception as e:
                    if not strict:
                        self._log(f"⚠ Could not process {level_type} level: \n{e}", to_stdout=verbose)
                    else:
                        raise
                    
            elif self.engine == 'diann':
                # For DIA-NN data, split the raw DataFrame by level
                temp_path = None
                source_path = None
                df_to_write = results_df
                
                if '_source_zip' in results_df.columns:
                    source_path = results_df['_source_zip'].iloc[0] if len(results_df) > 0 else None
                    df_to_write = results_df.drop(columns=['_source_zip'])
                    
                try:
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.tsv', delete=False) as temp_file:
                        df_to_write.to_csv(temp_file.name, sep='\t', index=False)
                        temp_path = temp_file.name
                    
                    # Check available levels
                    available_levels = self.loader.check_available_levels(temp_path, sections=sections)
                    
                    if verbose:
                        self._log(f"  Available levels: {list(available_levels.keys())}", to_stdout=verbose)

                    # Load each requested level
                    for level in levels:
                        if level not in available_levels:
                            continue
                            
                        try:
                            self._log(f"  Extracting {level} level...", to_stdout=verbose)
                            df = self.loader.load_to_level_df(
                                temp_path,
                                level=level,
                                sections=sections,
                                strict=False,
                                source_path=source_path
                            )
                            level_dfs[level].append(df)
                            self._log(f"    ✓ {level}: {df.shape}", to_stdout=verbose)
                        except Exception as e:
                            if not strict:
                                self._log(f"⚠ Could not extract {level} level: \n{e}", to_stdout=verbose)
                            else:
                                raise
                            
                except Exception as e:
                    self._log(f"⚠ Error transforming {sample_id}: {e}")
                finally:
                    if temp_path:
                        try:
                            os.unlink(temp_path)
                        except:
                            pass
        
        return level_dfs

    def _load_result_dfs_from_paths(
        self,
        file_paths: Dict[str, str],
        levels: List[str],
        sections: Optional[List[str]] = None,
        strict: bool = False,
        verbose: bool = False
    ) -> Dict[str, List[pd.DataFrame]]:
        """
        Load and transform raw result files into level-specific DataFrames.
        
        Parameters:
        -----------
        file_paths : Dict[str, str]
            Dictionary mapping sample IDs to file paths
        levels : List[str]
            Levels to load (precursor, protein, gene, peptide)
        sections : List[str], optional
            Specific sections to include
        strict : bool
            If True, raise error if expected columns are missing
        verbose : bool
            Whether to log verbose output
        
        Returns:
        --------
        Dict[str, List[pd.DataFrame]]
            Dictionary mapping levels to lists of DataFrames
        """
        # Step 1: Load raw files
        raw_dfs = self._load_raw_result_dfs(file_paths, verbose=verbose)
        
        # Step 2: Transform by level
        level_dfs = self._transform_raw_dfs_by_level(
            raw_dfs, 
            levels=levels, 
            sections=sections, 
            strict=strict, 
            verbose=verbose
        )
        
        return level_dfs

    def _merge_level_dfs(
        self,
        level_dfs: Dict[str, List[pd.DataFrame]],
        verbose: bool = False
    ) -> Dict[str, pd.DataFrame]:
        """
        Merge DataFrames for each level.
        
        Parameters:
        -----------
        level_dfs : Dict[str, List[pd.DataFrame]]
            Dictionary mapping levels to lists of DataFrames
        verbose : bool
            Whether to log verbose output
        
        Returns:
        --------
        Dict[str, pd.DataFrame]
            Dictionary mapping levels to merged DataFrames
        """
        merged_dfs = {}
        
        self._log("\nMerging DataFrames across levels...", to_stdout=verbose)
        
        for level, dfs in level_dfs.items():
            if not dfs:
                continue
                
            self._log(f"  Merging {len(dfs)} DataFrames for {level} level...", to_stdout=verbose)
            
            # Apply search_path_index logic if needed
            all_search_paths = set()
            for df in dfs:
                if 'search_path' in df.columns:
                    all_search_paths.update(df['search_path'].unique())
            
            if len(all_search_paths) > 1:
                self._log(f"  Found {len(all_search_paths)} unique search paths. Creating search_path_index...", to_stdout=verbose)
                search_path_to_index = {path: idx for idx, path in enumerate(sorted(all_search_paths))}
                
                for df in dfs:
                    if 'search_path' in df.columns:
                        df['search_path_index'] = df['search_path'].map(search_path_to_index)
            
            # Concatenate DataFrames
            merged_df = pd.concat(dfs, axis=0, ignore_index=True)
            merged_dfs[level] = merged_df
            self._log(f"    ✓ Merged {level}: {merged_df.shape}", to_stdout=verbose)
        
        return merged_dfs

    def add_searches_from_dfs(
        self,
        level_dfs: Dict[str, pd.DataFrame],
        levels: Optional[List[str]] = None,
        sections: Optional[List[str]] = None,
        verbose: bool = False
    ):
        """
        Add merged DataFrames to collection as AnnData objects.
        
        Parameters:
        -----------
        level_dfs : Dict[str, pd.DataFrame]
            Dictionary mapping levels to merged DataFrames
        levels : List[str], optional
            Specific levels to add (if None, adds all levels in level_dfs)
        sections : List[str], optional
            Specific sections to include
        verbose : bool
            Whether to log verbose output
        """
        if levels is None:
            levels = list(level_dfs.keys())
        
        # Commit any pending column configurations before converting to AnnData
        if self.pending_column_configs:
            self.commit_column_configs(verbose=verbose)
        
        self._log("\nConverting DataFrames to AnnData objects...", to_stdout=verbose)
        
        for level in levels:
            if level not in level_dfs:
                continue
                
            concat_df = level_dfs[level]
            
            # Convert to AnnData
            adata = self.loader.load_to_adata(
                concat_df,
                level=level,
                sections=sections,
                strict=False
            )

            # If level already exists in collection, concatenate with existing data
            if level in self.data:
                self._log(f"  Concatenating with existing {level} data...", to_stdout=verbose)
                existing = self.data[level]

                # Merge obs metadata separately
                merged_obs = pd.concat([existing.obs, adata.obs], axis=0).drop_duplicates()

                adata = ad.concat(
                    [existing, adata],
                    axis=1,  # Concatenate along var (columns/samples) axis
                    join='outer',
                    merge=None
                )
                
                merged_obs = merged_obs.reindex(index=adata.obs_names, fill_value=np.nan)
                adata.obs = merged_obs
                adata.obs_names = merged_obs.index
                
                self.data[level] = adata
                self._log(f"  ✓ Concatenated {level} with shape: {self.data[level].shape}", to_stdout=verbose)
            else:
                # First time adding this level
                self.data[level] = adata
                self._log(f"  ✓ Added new {level} level with shape: {self.data[level].shape}", to_stdout=verbose)

    def _load_result_file_dfs(
        self,
        path: str,
        metadata: Optional[pd.DataFrame] = None,
        levels: Optional[List[str]] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        DEPRECATED: Use the new workflow functions instead.
        Find and return results data as dfs using helper functions for different search types.
        
        Parameters:
        -----------
        path: str
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
        # Use new workflow
        file_paths = self._find_result_file_paths_single(path, metadata=metadata, levels=levels)
        results_data = {}
        for sample_id, file_path in file_paths.items():
            results_data[sample_id] = self._read_raw_result_file(file_path, sample_id)
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
    
    def _find_all_results_file_paths(
        self,
        paths: str | list,
        levels: Optional[List[str]] = None,
        metadata: Optional[pd.DataFrame] = None,
        verbose: bool = False
    ) -> Dict[str, str]:
        """
        Load search results from a folder or zip and add to collection.

        Parameters:
        -----------
        paths : str | list
            Path to folder or zip file containing search results, or a list of such paths    
        levels : List[str], optional
            Specific levels to load (precursor, protein, gene, peptide)
            If None, loads all available levels
        metadata : pd.DataFrame, optional
            Metadata dataframe with 'processing_run_uuid' column to filter specific searches.
            If provided, only loads search results matching the UUIDs in the metadata.
            This allows loading only specific searches from large zip files instead of 
            extracting everything.
        """
        # Convert single path to list for uniform handling
        paths = paths if isinstance(paths, list) else [paths]
        
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
            return all_results_data

        self._log(f"Found {len(all_results_data)} result samples ({self.search_type} format)", to_stdout=verbose)
        
        # Log which UUIDs were found if metadata filtering was used
        if target_uuids is not None:
            found_uuids = set(all_results_data.keys())
            missing_uuids = target_uuids - found_uuids
            if found_uuids:
                self._log(f"Successfully found {len(found_uuids)} searches from metadata", to_stdout=verbose)
            if missing_uuids:
                self._log(f"Warning: {len(missing_uuids)} searches from metadata not found: {missing_uuids}", to_stdout=verbose)

        return all_results_data

    def add_searches(
        self,
        paths: str | list,
        levels: Optional[List[str]] = None,
        sections: Optional[List[str]] = None,
        strict: bool = False,
        metadata: Optional[pd.DataFrame] = None,
        transformations: Optional[List[Dict]] = None,
        commit_immediately: bool = False,
        verbose: bool = False
    ):
        """
        Load search results from a folder or zip and add to collection.

        Parameters:
        -----------
        paths : str | list
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
        transformations : List[Dict], optional
            List of transformation specifications to apply to raw DataFrames before
            converting to AnnData. See load_results() for format.
        commit_immediately : bool
            If True, commit column configs immediately. If False (default),
            configs are automatically committed when adding to collection.
        verbose : bool
            Whether to log verbose output
        """
        # Workflow step 1-3: Load raw results (with optional transformations)
        raw_dfs = self.load_results(paths, metadata=metadata, transformations=transformations, commit_immediately=commit_immediately, verbose=verbose)
        
        if not raw_dfs:
            self._log(f"⚠ No result files found. Exiting.", to_stdout=verbose)
            return
        
        # Workflow step 4-5: Transform raw results into merged level DataFrames
        if levels is None:
            levels = list(self.loader.config['levels'].keys())
        
        merged_dfs = self.transform_to_levels(
            raw_dfs, 
            levels=levels, 
            sections=sections, 
            strict=strict, 
            verbose=verbose
        )
        
        # Workflow step 6: Add merged DataFrames to collection as AnnData objects
        self.add_searches_from_dfs(merged_dfs, levels=levels, sections=sections, verbose=verbose)

    def load_results(
        self,
        paths: str | list,
        metadata: Optional[pd.DataFrame] = None,
        transformations: Optional[List[Dict]] = None,
        commit_immediately: bool = False,
        verbose: bool = False
    ) -> Dict[str, pd.DataFrame]:
        """
        Load raw search results from folders or zips.

        Parameters:
        -----------
        paths : str | list
            Path to folder or zip file containing search results, or a list of such paths
        metadata : pd.DataFrame, optional
            Metadata dataframe with 'processing_run_uuid' column to filter specific searches.
            If provided, only loads search results matching the UUIDs in the metadata.
        transformations : List[Dict], optional
            List of transformation specifications to apply to raw DataFrames.
            Each dict should contain:
            - 'column_name': str - Name of the new column
            - 'function': callable or str - Function to apply or string expression
            - 'storage': str - Where to store ('var', 'obs', or 'layer')
            - 'levels': List[str] or None - Which levels to apply to
            - 'section': str - Section name (default: 'optional')
        commit_immediately : bool
            If True, commit column configs immediately. If False (default),
            store as pending configs.
        verbose : bool
            Whether to log verbose output
            
        Returns:
        --------
        Dict[str, pd.DataFrame]
            Dictionary mapping sample IDs to raw result DataFrames
        """
        # Workflow step 1 & 2: Find all result file paths
        # Note: levels parameter only used for Spectronaut to filter peptide/protein files
        file_paths = self._find_all_result_file_paths(paths, metadata=metadata, levels=None, verbose=verbose)
        
        if not file_paths:
            self._log(f"⚠ No result files found.", to_stdout=verbose)
            return {}
        
        # Workflow step 3: Load raw result files
        raw_dfs = self._load_raw_result_dfs(file_paths, verbose=verbose)
        
        # Workflow step 3b (optional): Apply transformations to add computed columns
        if transformations:
            raw_dfs = self.add_computed_columns(raw_dfs, transformations, commit_immediately=commit_immediately, verbose=verbose)
        
        return raw_dfs

    def transform_to_levels(
        self,
        raw_dfs: Dict[str, pd.DataFrame],
        levels: Optional[List[str]] = None,
        sections: Optional[List[str]] = None,
        strict: bool = False,
        verbose: bool = False
    ) -> Dict[str, pd.DataFrame]:
        """
        Transform raw result DataFrames into merged level-specific DataFrames.

        Parameters:
        -----------
        raw_dfs : Dict[str, pd.DataFrame]
            Dictionary mapping sample IDs to raw result DataFrames
        levels : List[str], optional
            Specific levels to extract (precursor, protein, gene, peptide)
            If None, extracts all available levels
        sections : List[str], optional
            Specific sections to include
        strict : bool
            If True, raise error if expected columns are missing
        verbose : bool
            Whether to log verbose output
            
        Returns:
        --------
        Dict[str, pd.DataFrame]
            Dictionary mapping level names to merged DataFrames
        """
        # Determine which levels to extract
        if levels is None:
            levels = list(self.loader.config['levels'].keys())
        
        # Workflow step 4: Transform raw DataFrames by level
        level_dfs = self._transform_raw_dfs_by_level(
            raw_dfs, 
            levels=levels, 
            sections=sections, 
            strict=strict, 
            verbose=verbose
        )
        
        # Workflow step 5: Merge DataFrames for each level
        merged_dfs = self._merge_level_dfs(level_dfs, verbose=verbose)
        
        return merged_dfs

    def add_dfs_to_collection(self,
                          levels_dfs: Union[Dict[str, pd.DataFrame], pd.DataFrame],
                          levels: Optional[Union[str, list, None]] = None,
                          sections: Optional[List[str]] = None):
        """
        Add DataFrames to collection by converting them to AnnData objects.
        
        Parameters:
        -----------
        levels_dfs : Union[Dict[str, pd.DataFrame], pd.DataFrame]
            Dictionary mapping level names to concatenated DataFrames or a single DataFrame
        levels : str, list, or None
            Specific levels to process. If None, processes all levels in levels_dfs
        sections : List[str], optional
            Specific sections to include
        """
        if levels is None:
            if isinstance(levels_dfs, pd.DataFrame):
                raise ValueError("If loading single DataFrame, you must specify the level name in 'levels' parameter.")
            else:
                levels = list(levels_dfs.keys())
        if isinstance(levels, str):
            levels = [levels]
        
        # Commit any pending column configurations before converting to AnnData
        if self.pending_column_configs:
            self.commit_column_configs(verbose=False)
        
        for level in levels:
            concat_df = levels_dfs[level]
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
                # need to perform separate obs merge to ensure we keep all obs metadata from both existing and new data, 
                # and then reassign to adata.obs after the var concat
                merged_obs = pd.concat([existing.obs, adata.obs], axis=0).drop_duplicates()

                adata = ad.concat(
                    [existing, adata],
                    axis=1,  # Concatenate along var (columns/samples) axis
                    join='outer',
                    merge=None  # Keep first value for non-aligned obs metadata
                )
                
                merged_obs = merged_obs.reindex(index=adata.obs_names, fill_value=np.nan)
                adata.obs = merged_obs
                adata.obs_names = merged_obs.index
                
                self.data[level] = adata
                self._log(f"    ✓ Concatenated {level} with shape: {self.data[level].shape}")
            else:
                # First time adding this level
                self.data[level] = adata
                self._log(f"    ✓ Added new {level} level with shape: {self.data[level].shape}")

    def get(self, level: str, sample: Optional[str] = None):
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

    ## TODO: useless right now
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
    def from_file(cls,
                   filepath: str, 
                   container: str = "bps",
                   engine: str = "diann", 
                   config_path: Optional[str] = None,
                   search_type: Optional[str] = None
                   ):
        """
        Load collection from file.

        Parameters:
        -----------
        filepath : str
            Path to saved file
        container : str
            Data container type ('bps', 'fragpipe', 'diann')
        engine : str
            Search engine type ('diann', 'spectronaut')
        config_path : str
            Path to YAML configuration file
        search_type : str, optional
            DEPRECATED: Use container and engine parameters instead.

        Returns:
        --------
        SearchCollection
            Loaded collection
        """
        # Handle deprecated search_type parameter
        if search_type is not None:
            warnings.warn(
                "The 'search_type' parameter is deprecated. Use 'container' and 'engine' parameters instead.",
                DeprecationWarning,
                stacklevel=2
            )
            parts = search_type.split('_')
            if len(parts) == 2:
                container, engine = parts
            elif len(parts) == 1:
                if parts[0] in ['diann', 'spectronaut']:
                    engine = parts[0]
                    container = 'diann' if engine == 'diann' else 'bps'
                else:
                    container = parts[0]
                    engine = 'diann'

        if config_path is None:
            if engine == 'diann': 
                config_path = "diann_columns.yaml"
            elif engine == 'spectronaut':
                config_path = "spnt_columns.yaml"
            else:
                config_path = "diann_columns.yaml"
                
        filepath_obj = Path(filepath)
        collection = cls(container=container, engine=engine, config_path=config_path)

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
        return f"SearchCollection(levels={levels})"

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
