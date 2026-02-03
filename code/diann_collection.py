"""
DIA-NN Collection

A collection object for managing multiple DIA-NN search results, following the
same pattern as MSMethodCollection and LCMethodCollection.

Stores searches as combined AnnData objects by level for efficient access and manipulation.
"""

import pandas as pd
import anndata as ad
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

    def add_from_folder(
        self,
        folder_path: str,
        levels: Optional[List[str]] = None,
        sections: Optional[List[str]] = None,
        strict: bool = False,
        search_type: str = 'bps'
    ):
        """
        Load DIA-NN results from a folder or zip and add to collection.

        Parameters:
        -----------
        folder_path : str
            Path to folder or zip file containing DIA-NN search results
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
        folder_path_obj = Path(folder_path)

        # Check if path is a zip file or directory
        if folder_path_obj.is_file() and folder_path_obj.suffix == '.zip':
            # It's a zip file - extract it first
            temp_dir = tempfile.mkdtemp(prefix='diann_folder_')
            self.temp_dirs.append(temp_dir)

            try:
                with zipfile.ZipFile(folder_path, 'r') as zf:
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
                raise ValueError(f"Invalid zip file: {folder_path}")

        elif folder_path_obj.is_dir():
            # It's a directory - use it directly
            search_path = folder_path_obj

        else:
            raise ValueError(
                f"Path must be a directory or zip file: {folder_path}\n"
                f"Exists: {folder_path_obj.exists()}, "
                f"Is file: {folder_path_obj.is_file()}, "
                f"Is dir: {folder_path_obj.is_dir()}"
            )

        # Find all results files based on search type
        results_files = self._find_results_files(search_path, search_type=search_type)

        if not results_files:
            expected_structure = {
                'bps': 'tims-diann.result.zip/result.tsv or tims-diann.result/result.tsv',
                'fragpipe': 'sample/diann-output/report.tsv'
            }
            raise FileNotFoundError(
                f"No results files found in {folder_path} for search_type='{search_type}'. "
                f"Expected structure: {expected_structure[search_type]}"
            )

        self._log(f"Found {len(results_files)} DIA-NN result files ({search_type} format)")

        # Determine which levels to load
        if levels is None:
            levels = list(self.loader.config['levels'].keys())

        # Temporary storage for sample AnnData objects before concatenation
        level_samples: Dict[str, List[ad.AnnData]] = {level: [] for level in levels}

        # Load each results file at each level
        for sample_name, results_path in results_files:
            self._log(f"\nLoading {sample_name}...")

            # Check which levels are available FIRST (more efficient - only reads header)
            available_levels = self.loader.check_available_levels(
                str(results_path),
                sections=sections
            )

            # Try to load each requested level
            for level in levels:
                level_info = available_levels.get(level, {})

                # Show warning about missing columns but still attempt to load
                if not level_info.get('available', False):
                    missing = level_info.get('missing_columns', [])
                    self._log(f"  ⚠ Note: {level} level missing some columns: {', '.join(missing[:3])}{'...' if len(missing) > 3 else ''}")

                try:
                    self._log(f"  Loading {level} level...")

                    # Load with strict=False to be permissive
                    adata = self.loader.load_to_adata(
                        str(results_path),
                        level=level,
                        sections=sections,
                        strict=False
                    )

                    # Add sample UUID/name to var (sample-level metadata, not obs)
                    adata.var['UUID'] = sample_name

                    # Add search type to var
                    adata.var['search_type'] = search_type

                    # Add to temporary list for concatenation
                    level_samples[level].append(adata)

                    # Print AnnData summary
                    self._log(f"    ✓ {level}: {adata.shape}")
                    self._log(f"\n{adata}\n")

                except Exception as e:
                    # Handle errors during loading
                    if not strict:
                        self._log(f"    ⚠ Could not load {level} level: {type(e).__name__}")
                    else:
                        warnings.warn(f"Error loading {sample_name} at {level} level: {e}")
                    continue

        # return level_samples
        # Concatenate samples for each level
        self._log("\nCombining samples across levels...")
        for level in levels:
            if level_samples[level]:  # If we have any samples for this level
                self._log(f"  Combining {len(level_samples[level])} samples for {level} level...")

                # Concatenate all new samples for this level
                if len(level_samples[level]) == 1:
                    combined = level_samples[level][0]
                else:
                    combined = ad.concat(level_samples[level],
                        axis=1,  # Concatenate along var (columns/samples) axis
                        join='outer',
                        merge='first'  # Keep first value for non-aligned obs metadata
                    )

                # If level already exists in collection, concatenate with existing data
                if level in self.data:
                    self._log(f"    Concatenating with existing {level} data...")
                    existing = self.data[level]
                    combined = ad.concat(
                        [existing, combined],
                        axis=1,  # Concatenate along var (columns/samples) axis
                        join='outer',
                        merge='first'  # Keep first value for non-aligned obs metadata
                    )
                    self.data[level] = combined
                    self._log(f"    ✓ Combined shape: {self.data[level].shape}")
                else:
                    # First time adding this level
                    self.data[level] = combined
                    self._log(f"    ✓ Added {level} with shape: {self.data[level].shape}")

        self._log(f"\n✓ Added {len(results_files)} samples to collection")

    def add_single_search(
        self,
        search_path: str,
        sample_name: Optional[str] = None,
        levels: Optional[List[str]] = None,
        sections: Optional[List[str]] = None,
        strict: bool = False,
        search_type: str = 'bps'
    ):
        """
        Load DIA-NN results from a single search folder and add to collection.

        Searches for tims-diann.result.zip or result.tsv/results.tsv in the folder
        using the same logic as add_from_folder.

        Parameters:
        -----------
        search_path : str
            Path to search folder (will look for tims-diann.result.zip or result.tsv)
            OR path to a .tsv file directly (for fragpipe search_type)
        sample_name : str, optional
            Name for this sample. If None, uses folder name or file stem
        levels : List[str], optional
            Specific levels to load (precursor, protein, gene)
            If None, loads all available levels
        sections : List[str], optional
            Specific sections to include
        strict : bool
            If True, raise error if expected columns are missing
        search_type : str
            Type of search structure ('bps' or 'fragpipe')

        Example:
        --------
        >>> collection = DiannCollection()
        >>> collection.add_single_search("sample1_folder/", sample_name="sample1")
        >>> collection.add_single_search("sample2_folder/", sample_name="sample2")
        >>> # For FragPipe, can also provide direct path to .tsv file
        >>> collection.add_single_search("results.tsv", search_type='fragpipe')
        """
        search_path_obj = Path(search_path)

        if not search_path_obj.exists():
            raise FileNotFoundError(f"Path not found: {search_path}")

        # Check if path is directly a .tsv file
        if search_path_obj.is_file() and search_path_obj.suffix == '.tsv':
            # Direct .tsv file path provided
            results_file_path = search_path_obj
            detected_sample_name = search_path_obj.stem
            self._log(f"Loading from direct .tsv file: {results_file_path.name}")
        elif search_path_obj.is_dir():
            # Directory path - search for results 
            # Use _find_results_files to locate the results file
            results_files = self._find_results_files(search_path_obj, search_type)

            if len(results_files) == 0:
                raise FileNotFoundError(
                    f"No results files found in {search_path} for search_type='{search_type}'. "
                    f"Expected structure for {search_type}."
                )

            if len(results_files) > 1:
                warnings.warn(
                    f"Found {len(results_files)} results files in {search_path}. "
                    f"Will load only the first one: {results_files[0][0]}"
                )

            # Get the first (and should be only) result file
            detected_sample_name, results_file_path = results_files[0]
        else:
            raise ValueError(f"Path must be a directory or .tsv file: {search_path}")

        # Determine sample name
        if sample_name is None:
            sample_name = detected_sample_name  # Use the detected sample name from folder structure or file stem

        # Determine which levels to load
        if levels is None:
            levels = list(self.loader.config['levels'].keys())

        self._log(f"\nLoading {sample_name} from {results_file_path.name}...")

        # Check which levels are available
        available_levels = self.loader.check_available_levels(
            str(results_file_path),
            sections=sections
        )

        # Storage for loaded samples by level
        level_samples: Dict[str, List[ad.AnnData]] = {level: [] for level in levels}

        # Try to load each requested level
        for level in levels:
            level_info = available_levels.get(level, {})

            # Show warning about missing columns but still attempt to load
            if not level_info.get('available', False):
                missing = level_info.get('missing_columns', [])
                self._log(f"  ⚠ Note: {level} level missing some columns: {', '.join(missing[:3])}{'...' if len(missing) > 3 else ''}")

            try:
                self._log(f"  Loading {level} level...")

                # Load with strict=False to be permissive
                adata = self.loader.load_to_adata(
                    str(results_file_path),
                    level=level,
                    sections=sections,
                    strict=False
                )

                # Add sample UUID/name to var (sample-level metadata, not obs)
                adata.var['UUID'] = sample_name

                # Add search type to var
                adata.var['search_type'] = search_type

                # Add to temporary list for potential concatenation
                level_samples[level].append(adata)

                # Log success
                self._log(f"    ✓ {level}: {adata.shape}")

            except Exception as e:
                # Handle errors during loading
                if not strict:
                    self._log(f"    ⚠ Could not load {level} level: {type(e).__name__}")
                else:
                    raise

        # Add or concatenate with existing data
        self._log(f"\nAdding to collection...")
        for level in levels:
            if level_samples[level]:  # If we have any samples for this level
                self._log(f"  Adding {level} level...")

                # Concatenate all new samples for this level (should be 1 for single search)
                if len(level_samples[level]) == 1:
                    combined = level_samples[level][0]
                else:
                    combined = ad.concat(level_samples[level],
                        axis=1,  # Concatenate along var (columns/samples) axis
                        join='outer',
                        merge='first'  # Keep first value for non-aligned obs metadata
                    )

                # If level already exists in collection, concatenate with existing data
                if level in self.data:
                    self._log(f"    Concatenating with existing {level} data...")
                    existing = self.data[level]
                    combined = ad.concat(
                        [existing, combined],
                        axis=1,  # Concatenate along var (columns/samples) axis
                        join='outer',
                        merge='first'  # Keep first value for non-aligned obs metadata
                    )
                    self.data[level] = combined
                    self._log(f"    ✓ Combined shape: {self.data[level].shape}")
                else:
                    # First time adding this level
                    self.data[level] = combined
                    self._log(f"    ✓ Added {level} with shape: {self.data[level].shape}")

        self._log(f"\n✓ Added sample '{sample_name}' to collection")

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
            mask = adata.var['UUID'] == sample
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
            return sorted(self.data[level].var['UUID'].unique().tolist())
        else:
            # Return union of all samples across all levels
            all_samples = set()
            for adata in self.data.values():
                if 'Sample' in adata.var.columns:
                    all_samples.update(adata.var['UUID'].unique())
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
            mask = adata.var['UUID'].isin(samples)
            adata = adata[:, mask].copy()

        # Convert to DataFrame (long format)
        # This creates a melted format with genes × samples
        df_list = []
        for i, sample in enumerate(adata.var['UUID']):
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
                samples = adata.var['UUID'].unique()
                for sample in samples:
                    # Each sample is a column, so n_obs is constant across samples
                    summary_data.append({
                        'Sample': sample,
                        'Level': level,
                        'n_obs': adata.n_obs,  # Number of genes/proteins/precursors
                        'n_vars': 1,  # Each sample is one column
                        'shape': f"({n_obs}, {adata.n_vars})"
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
        n_samples = len(self.list_samples())
        levels = list(self.data.keys())
        return f"DiannCollection(samples={n_samples}, levels={levels})"

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
