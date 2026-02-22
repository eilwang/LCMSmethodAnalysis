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
from anndiannloader import DiannLoader


class DiannCollection:
    """
    Collection object for managing multiple DIA-NN search results.

    Stores searches as combined AnnData objects internally, organized by level.
    Each level contains all samples concatenated together.
    """

    def __init__(self, config_path: str = "diann_columns.yaml", log_file: Optional[str] = None):
        """
        Initialize DIA-NN collection.

        Parameters:
        -----------
        config_path : str
            Path to YAML configuration file defining column mappings
        log_file : str, optional
            Path to log file. If provided, all print output will be written to this file.
            If None, output goes to stdout only.
        """
        self.loader = DiannLoader(config_path)
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

    def _log(self, message: str, to_stdout: bool = None):
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

    def _get_search_path(self, 
                        path: str) -> Path:
        
        path_obj = Path(path)

        # Check if path is a zip file or directory
        if path_obj.is_file():
            # check if zip folder
            if path_obj.suffix == '.tsv':
                search_path = path_obj
            elif path_obj.suffix == '.zip':
            # It's a zip file - extract it first
                temp_dir = tempfile.mkdtemp(prefix='diann_folder_')
                self.temp_dirs.append(temp_dir)

                try:
                    with zipfile.ZipFile(path_obj, 'r') as zf:
                        zf.extractall(temp_dir)
                    search_path = Path(temp_dir)

                    # Check if extraction created a single wrapper folder
                    # If so, start searching from that folder instead
                    contents = list(search_path.iterdir())
                    if len(contents) == 1 and contents[0].is_dir():
                        # Common case: zip creates a single top-level folder
                        # e.g., archive.zip -> temp_dir/processing-run/
                        search_path = contents[0]

                except zipfile.BadZipFile:
                    raise ValueError(f"Invalid zip file: {path}")

        elif path_obj.is_dir():
            # It's a directory - use it directly
            search_path = path_obj

        else:
            raise ValueError(
                f"Path must be a directory or zip file: {path}\n"
                f"Exists: {path_obj.exists()}, "
                f"Is file: {path_obj.is_file()}, "
                f"Is dir: {path_obj.is_dir()}"
            )

        # Find all results files based on search type
        return search_path

    def _find_results_files(
        self,
        search_dir: Path,
        search_type: str = 'bps'
    ) -> List[Tuple[str, Path]]:
        """
        Find all results files in a directory structure based on search type.

        Parameters:
        -----------
        search_dir : Path
            Directory to search in
        search_type : str
            Type of search output structure:
            - 'bps': tims-diann.result.zip/result.tsv or tims-diann.result/result.tsv
            - 'fragpipe': sample/diann-output/report.tsv

        Returns:
        --------
        List[Tuple[str, Path]]
            List of (sample_name, results_file_path) tuples
        """
        results_files = []

        if search_type == 'bps':
            # BPS structure: tims-diann.result.zip with result.tsv or results.tsv
            # Recursively search for tims-diann.result.zip files

            # TSV patterns to search for (both singular and plural)
            tsv_patterns = ["result.tsv", "results.tsv"]

            # Look for result.tsv or results.tsv files directly
            for pattern in tsv_patterns:
                for tsv_file in search_dir.rglob(pattern):
                    # Use parent directory name as sample name
                    sample_name = tsv_file.parent.name
                    if sample_name.endswith('.result'):
                        sample_name = sample_name[:-7]
                    results_files.append((sample_name, tsv_file))

            # Recursively search for tims-diann.result.zip or any .result.zip files
            for zip_file in search_dir.rglob("*.zip"):
                if not (zip_file.name.endswith('.result.zip') or 'tims-diann' in zip_file.name.lower()):
                    continue

                try:
                    temp_dir = tempfile.mkdtemp(prefix='diann_extract_')
                    self.temp_dirs.append(temp_dir)

                    with zipfile.ZipFile(zip_file, 'r') as zf:
                        zf.extractall(temp_dir)

                    temp_path = Path(temp_dir)
                    # Search for both result.tsv and results.tsv
                    found = False
                    for pattern in tsv_patterns:
                        for tsv_file in temp_path.rglob(pattern):
                            # Use parent directory of the zip as sample name
                            sample_name = zip_file.parent.name
                            if sample_name.endswith('.result'):
                                sample_name = sample_name[:-7]
                            results_files.append((sample_name, tsv_file))
                            found = True
                            break
                        if found:
                            break
                except zipfile.BadZipFile:
                    warnings.warn(f"Skipping invalid zip file: {zip_file}")
                    continue
                except Exception as e:
                    warnings.warn(f"Error processing {zip_file}: {e}")
                    continue

        elif search_type == 'fragpipe':
            # FragPipe structure: sample/diann-output/report.tsv
            for tsv_file in search_dir.rglob("diann-output/report.tsv"):
                # Use grandparent directory name as sample name (parent is diann-output)
                sample_name = tsv_file.parent.parent.name
                results_files.append((sample_name, tsv_file))

        else:
            raise ValueError(f"Unknown search_type: {search_type}. Must be 'bps' or 'fragpipe'")

        return results_files
    


    def add_searches(
        self,
        path: str | list,
        levels: Optional[List[str]] = None,
        sections: Optional[List[str]] = None,
        strict: bool = False,
        search_type: str = 'bps'
    ):
        """
        Load DIA-NN results from a folder or zip and add to collection.

        Parameters:
        -----------
        folder_path : str | list
            Path to folder or zip file containing DIA-NN search results, or a list of such paths    
        levels : List[str], optional
            Specific levels to load (precursor, protein, gene)
            If None, loads all available levels
        sections : List[str], optional
            Specific sections to include
        strict : bool
            If True, raise error if expected columns are missing
        search_type : str
            Type of search output structure:
            - 'bps': tims-diann.result.zip/result.tsv (default)
            - 'fragpipe': sample/diann-output/report.tsv
        """
        # Convert single path to list for uniform handling
        paths = path if isinstance(path, list) else [path]
        
        results_files = []
        for p in paths:
            search_path = self._get_search_path(p)
            results_files.extend(self._find_results_files(search_path, search_type=search_type))

        if not results_files:
            expected_structure = {
                'bps': 'tims-diann.result.zip/result.tsv or tims-diann.result/result.tsv',
                'fragpipe': 'sample/diann-output/report.tsv'
            }
            raise FileNotFoundError(
                f"No results files found in {path} for search_type='{search_type}'. "
                f"Expected structure: {expected_structure[search_type]}"
            )

        self._log(f"Found {len(results_files)} DIA-NN result files ({search_type} format)")

        # Determine which levels to load
        if levels is None:
            levels = list(self.loader.config['levels'].keys())

        # Temporary storage for sample AnnData objects before concatenation
        level_samples: Dict[str, List[ad.AnnData]] = {level: [] for level in levels}

        # Load each results file at each level
        for uuid, results_path in results_files:
            self._log(f"\nLoading {uuid}")

            # Check which levels are available FIRST (more efficient - only reads header)
            available_levels = self.loader.check_available_levels(
                str(results_path),
                sections=sections
            )

            # Try to load each requested level
            for level in levels:
                level_info = available_levels.get(level, {})

                # # Show warning about missing columns but still attempt to load
                # if not level_info.get('available', False):
                #     missing = level_info.get('missing_columns', [])
                #     msg = "\n".join(missing)
                #     # self._log(f"  ⚠ Note: {level} level missing some columns: {msg}")

                try:
                    self._log(f"  Loading {level} level...")

                        # Load with strict=False to be permissive
                    df = self.loader.load_to_df(
                            str(results_path),
                            level=level,
                            sections=sections,
                            strict=False,
                            search_type=search_type
                    )

                    # # Add sample UUID/name to var (sample-level metadata, not obs)
                    if search_type == 'bps':
                        df['UUID'] = uuid

                    # # Add to temporary list for concatenation
                    level_samples[level].append(df)

                        # Print AnnData summary
                    self._log(f"    ✓ {level}: {df.shape}")
                    self._log(f"\n{df}\n")

                except Exception as e:
                    # Handle errors during loading
                    if not strict:
                        self._log(f"⚠ Could not load {level} level: \n{e}")
                    else:
                        self._log(f"Error loading {uuid} at {level} level: {e}")
                        break
                    continue
        # return level_samples
        # Concatenate samples for each level
        self._log("\nCombining samples across levels...")

        for level in levels:
            if level_samples[level]:  # If we have any samples for this level
                self._log(f"  Combining {len(level_samples[level])} samples for {level} level...")

                concat_df = pd.concat(level_samples[level], axis=0, ignore_index=True)
                
                adata = self.loader.load_to_adata(
                            concat_df,
                            level=level,
                            sections=sections,
                            strict=False,
                            search_type=search_type
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
                self._log(f"    ✓ Added {level} with shape: {self.data[level].shape}")

        self._log(f"\n✓ Added {len(results_files)} samples to collection")

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
    def from_file(cls, filepath: str, config_path: str = "diann_columns.yaml") -> 'DiannCollection':
        """
        Load collection from file.

        Parameters:
        -----------
        filepath : str
            Path to saved file
        config_path : str
            Path to YAML configuration file

        Returns:
        --------
        DiannCollection
            Loaded collection
        """
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
        return f"DiannCollection(levels={levels})"

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
