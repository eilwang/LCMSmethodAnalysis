"""
DIA-NN Collection Loader

This module provides functionality to load multiple DIA-NN search results from
a zip folder structure, create DiannLoader objects for each, and merge them
at different analysis levels (precursor, protein, gene).
"""

import pandas as pd
import anndata as ad
import zipfile
import tempfile
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Union, Tuple
import warnings
from anndiannloader import DiannLoader


class DiannCollectionLoader:
    """
    Load and merge multiple DIA-NN search results from zip archives.

    This class handles zip folders containing multiple DIA-NN searches,
    where each search has a zipped folder (e.g., "tims-diann.result.zip")
    containing a "results.tsv" file.
    """

    def __init__(self, config_path: str = "diann_columns.yaml"):
        """
        Initialize with DIA-NN column configuration file.

        Parameters:
        -----------
        config_path : str
            Path to YAML configuration file defining column mappings
        """
        self.loader = DiannLoader(config_path)
        self.temp_dirs: List[str] = []  # Track temp dirs for cleanup

    def _find_results_files(self, search_dir: Path) -> List[Tuple[str, Path]]:
        """
        Find all results.tsv files in a directory structure.

        Searches for:
        1. Direct results.tsv files
        2. results.tsv files inside nested zip files (e.g., tims-diann.result.zip)

        Parameters:
        -----------
        search_dir : Path
            Directory to search in

        Returns:
        --------
        List[Tuple[str, Path]]
            List of (sample_name, results_file_path) tuples
        """
        results_files = []

        # Look for direct results.tsv files
        for tsv_file in search_dir.rglob("results.tsv"):
            # Use parent directory name as sample name
            sample_name = tsv_file.parent.name
            results_files.append((sample_name, tsv_file))

        # Look for zip files that might contain results.tsv
        for zip_file in search_dir.rglob("*.zip"):
            try:
                # Extract zip to temp directory
                temp_dir = tempfile.mkdtemp(prefix='diann_extract_')
                self.temp_dirs.append(temp_dir)

                with zipfile.ZipFile(zip_file, 'r') as zf:
                    zf.extractall(temp_dir)

                # Search extracted content for results.tsv
                temp_path = Path(temp_dir)
                for tsv_file in temp_path.rglob("results.tsv"):
                    # Use zip file name (without extension) as sample name
                    sample_name = zip_file.stem
                    # If it ends with .result, remove that too
                    if sample_name.endswith('.result'):
                        sample_name = sample_name[:-7]  # Remove '.result'
                    results_files.append((sample_name, tsv_file))
            except zipfile.BadZipFile:
                warnings.warn(f"Skipping invalid zip file: {zip_file}")
                continue
            except Exception as e:
                warnings.warn(f"Error processing {zip_file}: {e}")
                continue

        return results_files

    def load_from_zip(
        self,
        zip_path: str,
        level: Optional[str] = None,
        sections: Optional[List[str]] = None,
        strict: bool = False,
        merge_method: str = 'outer'
    ) -> Union[pd.DataFrame, Dict[str, pd.DataFrame]]:
        """
        Load and merge DIA-NN results from a zip archive.

        Parameters:
        -----------
        zip_path : str
            Path to zip file containing multiple DIA-NN search results
        level : str or None, optional
            Analysis level (precursor, protein, gene)
            If None or 'all', loads all available levels
        sections : List[str], optional
            Specific sections to include
        strict : bool
            If True, raise error if expected columns are missing
        merge_method : str
            How to merge DataFrames: 'outer', 'inner', or 'concat'
            - 'outer': Include all features from all samples (default)
            - 'inner': Only include features present in all samples
            - 'concat': Concatenate all DataFrames (creates long format)

        Returns:
        --------
        pd.DataFrame or Dict[str, pd.DataFrame]
            If level is specified: Merged DataFrame with all samples
            If level is None/'all': Dictionary with keys as level names and DataFrames as values
        """
        # If level is None or 'all', load all levels
        if level is None or level == 'all':
            available_levels = list(self.loader.config['levels'].keys())
            print(f"Loading all levels: {', '.join(available_levels)}")

            results = {}
            for lvl in available_levels:
                print(f"\n{'=' * 80}")
                print(f"Loading level: {lvl}")
                print(f"{'=' * 80}")
                try:
                    results[lvl] = self.load_from_zip(
                        zip_path,
                        level=lvl,
                        sections=sections,
                        strict=strict,
                        merge_method=merge_method
                    )
                except Exception as e:
                    warnings.warn(f"Error loading level '{lvl}': {e}")
                    continue

            if not results:
                raise ValueError("No levels could be loaded successfully")

            print(f"\n{'=' * 80}")
            print(f"✓ Successfully loaded {len(results)} levels")
            print(f"{'=' * 80}")
            for lvl, df in results.items():
                print(f"  {lvl}: {df.shape}")

            return results

        # Single level loading (original behavior)
        # Extract main zip to temp directory
        main_temp_dir = tempfile.mkdtemp(prefix='diann_main_')
        self.temp_dirs.append(main_temp_dir)

        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(main_temp_dir)

            # Find all results.tsv files
            results_files = self._find_results_files(Path(main_temp_dir))

            if not results_files:
                raise FileNotFoundError(
                    f"No results.tsv files found in {zip_path}. "
                    "Expected structure: zip containing folders with results.tsv "
                    "or nested zip files (e.g., tims-diann.result.zip) with results.tsv"
                )

            print(f"Found {len(results_files)} DIA-NN result files")

            # Load each results file
            dfs = []
            sample_names = []

            for sample_name, results_path in results_files:
                print(f"\nLoading {sample_name}...")
                try:
                    df = self.loader.load_to_df(
                        str(results_path),
                        level=level,
                        sections=sections,
                        strict=strict
                    )

                    # Add sample name as a column
                    df['Sample'] = sample_name
                    dfs.append(df)
                    sample_names.append(sample_name)
                except Exception as e:
                    warnings.warn(f"Error loading {sample_name}: {e}")
                    continue

            if not dfs:
                raise ValueError("No valid results files could be loaded")

            # Merge DataFrames
            print(f"\nMerging {len(dfs)} DataFrames using method '{merge_method}'...")
            merged_df = self._merge_dataframes(dfs, method=merge_method, level=level)

            print(f"\n✓ Successfully merged {len(sample_names)} samples: {', '.join(sample_names)}")
            print(f"  Final shape: {merged_df.shape}")

            return merged_df

        finally:
            # Cleanup handled in __del__ or explicit cleanup() call
            pass

    def load_from_folder(
        self,
        folder_path: str,
        level: Optional[str] = None,
        sections: Optional[List[str]] = None,
        strict: bool = False,
        merge_method: str = 'outer'
    ) -> Union[pd.DataFrame, Dict[str, pd.DataFrame]]:
        """
        Load and merge DIA-NN results from a folder or zip file.

        More flexible than load_from_zip - accepts either:
        - A directory containing results.tsv files or nested zips
        - A zip file containing results.tsv files or nested zips

        Parameters:
        -----------
        folder_path : str
            Path to folder or zip file containing DIA-NN search results
        level : str or None, optional
            Analysis level (precursor, protein, gene)
            If None or 'all', loads all available levels
        sections : List[str], optional
            Specific sections to include
        strict : bool
            If True, raise error if expected columns are missing
        merge_method : str
            How to merge DataFrames: 'outer', 'inner', or 'concat'
            - 'outer': Include all features from all samples (default)
            - 'inner': Only include features present in all samples
            - 'concat': Concatenate all DataFrames (creates long format)

        Returns:
        --------
        pd.DataFrame or Dict[str, pd.DataFrame]
            If level is specified: Merged DataFrame with all samples
            If level is None/'all': Dictionary with keys as level names and DataFrames as values
        """
        # If level is None or 'all', load all levels
        if level is None or level == 'all':
            available_levels = list(self.loader.config['levels'].keys())
            print(f"Loading all levels: {', '.join(available_levels)}")

            results = {}
            for lvl in available_levels:
                print(f"\n{'=' * 80}")
                print(f"Loading level: {lvl}")
                print(f"{'=' * 80}")
                try:
                    results[lvl] = self.load_from_folder(
                        folder_path,
                        level=lvl,
                        sections=sections,
                        strict=strict,
                        merge_method=merge_method
                    )
                except Exception as e:
                    warnings.warn(f"Error loading level '{lvl}': {e}")
                    continue

            if not results:
                raise ValueError("No levels could be loaded successfully")

            print(f"\n{'=' * 80}")
            print(f"✓ Successfully loaded {len(results)} levels")
            print(f"{'=' * 80}")
            for lvl, df in results.items():
                print(f"  {lvl}: {df.shape}")

            return results

        # Single level loading (original behavior)
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

        try:
            # Find all results.tsv files
            results_files = self._find_results_files(search_path)

            if not results_files:
                raise FileNotFoundError(
                    f"No results.tsv files found in {folder_path}. "
                    "Expected structure: folders with results.tsv "
                    "or nested zip files (e.g., tims-diann.result.zip) with results.tsv"
                )

            print(f"Found {len(results_files)} DIA-NN result files")

            # Load each results file
            dfs = []
            sample_names = []

            for sample_name, results_path in results_files:
                print(f"\nLoading {sample_name}...")
                try:
                    df = self.loader.load_to_df(
                        str(results_path),
                        level=level,
                        sections=sections,
                        strict=strict
                    )

                    # Add sample name as a column
                    df['Sample'] = sample_name
                    dfs.append(df)
                    sample_names.append(sample_name)
                except Exception as e:
                    warnings.warn(f"Error loading {sample_name}: {e}")
                    continue

            if not dfs:
                raise ValueError("No valid results files could be loaded")

            # Merge DataFrames
            print(f"\nMerging {len(dfs)} DataFrames using method '{merge_method}'...")
            merged_df = self._merge_dataframes(dfs, method=merge_method, level=level)

            print(f"\n✓ Successfully merged {len(sample_names)} samples: {', '.join(sample_names)}")
            print(f"  Final shape: {merged_df.shape}")

            return merged_df

        finally:
            # Cleanup handled in __del__ or explicit cleanup() call
            pass

    def load_to_adata_collection(
        self,
        zip_path: str,
        level: Optional[str] = None,
        sections: Optional[List[str]] = None,
        strict: bool = False,
        merge_obs: bool = True
    ) -> Union[ad.AnnData, Dict[str, ad.AnnData]]:
        """
        Load DIA-NN results from zip and create merged AnnData object.

        Parameters:
        -----------
        zip_path : str
            Path to zip file containing multiple DIA-NN search results
        level : str or None, optional
            Analysis level (precursor, protein, gene)
            If None or 'all', loads all available levels
        sections : List[str], optional
            Specific sections to include
        strict : bool
            If True, raise error if expected columns are missing
        merge_obs : bool
            If True, merge observations (samples) into single AnnData
            If False, keep separate AnnData objects per sample

        Returns:
        --------
        ad.AnnData or Dict[str, ad.AnnData]
            If level is specified: Merged AnnData object with all samples
            If level is None/'all': Dictionary with keys as level names and AnnData objects as values
        """
        # If level is None or 'all', load all levels
        if level is None or level == 'all':
            available_levels = list(self.loader.config['levels'].keys())
            print(f"Loading all levels to AnnData: {', '.join(available_levels)}")

            results = {}
            for lvl in available_levels:
                print(f"\n{'=' * 80}")
                print(f"Loading level: {lvl}")
                print(f"{'=' * 80}")
                try:
                    results[lvl] = self.load_to_adata_collection(
                        zip_path,
                        level=lvl,
                        sections=sections,
                        strict=strict,
                        merge_obs=merge_obs
                    )
                except Exception as e:
                    warnings.warn(f"Error loading level '{lvl}' to AnnData: {e}")
                    continue

            if not results:
                raise ValueError("No levels could be loaded successfully")

            print(f"\n{'=' * 80}")
            print(f"✓ Successfully loaded {len(results)} levels to AnnData")
            print(f"{'=' * 80}")
            for lvl, adata in results.items():
                print(f"  {lvl}: {adata.shape}")

            return results

        # Single level loading (original behavior)
        # Extract main zip to temp directory
        main_temp_dir = tempfile.mkdtemp(prefix='diann_main_')
        self.temp_dirs.append(main_temp_dir)

        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(main_temp_dir)

            # Find all results.tsv files
            results_files = self._find_results_files(Path(main_temp_dir))

            if not results_files:
                raise FileNotFoundError(
                    f"No results.tsv files found in {zip_path}"
                )

            print(f"Found {len(results_files)} DIA-NN result files")

            # Load each results file to AnnData
            adatas = []
            sample_names = []

            for sample_name, results_path in results_files:
                print(f"\nLoading {sample_name} to AnnData...")
                try:
                    adata = self.loader.load_to_adata(
                        str(results_path),
                        level=level,
                        sections=sections,
                        strict=strict
                    )

                    # Add sample name to obs
                    adata.obs['Sample'] = sample_name
                    adatas.append(adata)
                    sample_names.append(sample_name)
                except Exception as e:
                    warnings.warn(f"Error loading {sample_name}: {e}")
                    continue

            if not adatas:
                raise ValueError("No valid results files could be loaded")

            # Merge AnnData objects
            if merge_obs and len(adatas) > 1:
                print(f"\nMerging {len(adatas)} AnnData objects...")
                merged_adata = ad.concat(
                    adatas,
                    axis=0,  # Concatenate along observations (samples)
                    join='outer',  # Keep all variables
                    label='Sample_idx',
                    keys=sample_names,
                    index_unique='_'
                )

                print(f"✓ Successfully merged {len(sample_names)} samples")
                print(f"  Final shape: {merged_adata.shape}")
                return merged_adata
            else:
                # Return single AnnData or first one if merge_obs=False
                return adatas[0] if len(adatas) == 1 else adatas

        finally:
            pass

    def _merge_dataframes(
        self,
        dfs: List[pd.DataFrame],
        method: str = 'outer',
        level: str = 'precursor'
    ) -> pd.DataFrame:
        """
        Merge multiple DataFrames based on specified method.

        Parameters:
        -----------
        dfs : List[pd.DataFrame]
            List of DataFrames to merge
        method : str
            Merge method: 'outer', 'inner', or 'concat'
        level : str
            Analysis level (used to determine merge keys)

        Returns:
        --------
        pd.DataFrame
            Merged DataFrame
        """
        if method == 'concat':
            # Simple concatenation (long format)
            return pd.concat(dfs, ignore_index=True)

        # For outer/inner merge, need to determine appropriate keys
        # Get level config to determine merge keys
        level_config = self.loader.config['levels'][level]

        if method in ['outer', 'inner']:
            # Merge on common identifier columns
            # Use var columns as merge keys (e.g., Modified.Sequence, Precursor.Id)
            merge_keys = level_config.get('var', [])

            if not merge_keys:
                warnings.warn(
                    f"No merge keys found for level '{level}'. "
                    "Falling back to concat method."
                )
                return pd.concat(dfs, ignore_index=True)

            # Start with first DataFrame
            merged = dfs[0].copy()

            # Iteratively merge remaining DataFrames
            for df in dfs[1:]:
                merged = pd.merge(
                    merged,
                    df,
                    on=merge_keys,
                    how=method,
                    suffixes=('', '_dup')
                )

            return merged
        else:
            raise ValueError(
                f"Invalid merge method: {method}. "
                "Must be 'outer', 'inner', or 'concat'"
            )

    def cleanup(self):
        """Clean up temporary directories."""
        for temp_dir in self.temp_dirs:
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                warnings.warn(f"Could not remove temp directory {temp_dir}: {e}")
        self.temp_dirs.clear()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup temp files."""
        self.cleanup()

    def __del__(self):
        """Destructor - cleanup temp files."""
        self.cleanup()


# Usage example
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        zip_path = sys.argv[1]
    else:
        # Default example path
        zip_path = "/path/to/diann_searches.zip"
        print(f"Usage: python {sys.argv[0]} <path_to_zip>")
        print(f"\nExample structure expected:")
        print("  diann_searches.zip/")
        print("    ├── sample1-tims-diann.result.zip")
        print("    │   └── results.tsv")
        print("    ├── sample2-tims-diann.result.zip")
        print("    │   └── results.tsv")
        print("    └── ...")
        sys.exit(1)

    # Load and merge at precursor level
    with DiannCollectionLoader() as loader:
        print("=" * 80)
        print("LOADING PRECURSOR LEVEL DATA")
        print("=" * 80)

        df_precursor = loader.load_from_zip(
            zip_path,
            level="precursor",
            merge_method='concat'  # Keep all data in long format
        )

        print("\n" + "=" * 80)
        print("PRECURSOR DATA SUMMARY")
        print("=" * 80)
        print(f"Shape: {df_precursor.shape}")
        print(f"\nColumns: {list(df_precursor.columns)}")
        print(f"\nSamples: {df_precursor['Sample'].unique()}")
        print(f"\nFirst few rows:")
        print(df_precursor.head())

        # Load and merge at protein level
        print("\n" + "=" * 80)
        print("LOADING PROTEIN LEVEL DATA")
        print("=" * 80)

        df_protein = loader.load_from_zip(
            zip_path,
            level="protein",
            merge_method='concat'
        )

        print("\n" + "=" * 80)
        print("PROTEIN DATA SUMMARY")
        print("=" * 80)
        print(f"Shape: {df_protein.shape}")
        print(f"\nSamples: {df_protein['Sample'].unique()}")

        # Optionally create AnnData objects
        print("\n" + "=" * 80)
        print("CREATING ANNDATA OBJECT")
        print("=" * 80)

        adata = loader.load_to_adata_collection(
            zip_path,
            level="precursor",
            merge_obs=True
        )

        print(f"\nAnnData shape: {adata.shape}")
        print(f"Observations (runs): {adata.n_obs}")
        print(f"Variables (precursors): {adata.n_vars}")
        print(f"Layers: {list(adata.layers.keys())}")
