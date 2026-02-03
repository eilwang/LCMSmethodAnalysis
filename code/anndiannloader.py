from ctypes.util import test
import sys
import pandas as pd
import yaml
from typing import List, Optional, Dict
import warnings
import anndata as ad # pyright: ignore[reportMissingImports]
import numpy as np
import os
import logging

# Set up logger for this module
logger = logging.getLogger(__name__)

class DiannLoader:
    def __init__(self, config_path: str = "diann_columns.yaml"):
        """Initialize with DIA-NN column configuration file."""
        # If config_path is relative, resolve it relative to this module's directory
        if not os.path.isabs(config_path):
            module_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(module_dir, config_path)

        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
            
    def get_columns(
        self,
        level: str,
        sections: Optional[List[str]] = None
    ) -> List[str]:
        """
        Get column list for specified level.

        Parameters:
        -----------
        level : str
            Analysis level (precursor, protein, gene)
        sections : List[str], optional
            Specific sections to include (var, obs, pr_obs, x, mod_obs, optional)
            If None, includes all available sections

        Returns:
        --------
        List[str]
            List of column names
        """
        if level not in self.config['levels']:
            raise ValueError(
                f"Level '{level}' not found. Available: {list(self.config['levels'].keys())}"
            )

        level_config = self.config['levels'][level]
        cols = []

        # If sections not specified, include all available sections
        if sections is None:
            sections = list(level_config.keys())

        for section in sections:
            if section in level_config and level_config[section]:
                section_data = level_config[section]
                if isinstance(section_data, list):
                    cols.extend(section_data)

        return cols

    def get_section_columns(self, level: str, section: str) -> List[str]:
        """
        Get columns for a specific section within a level.

        Parameters:
        -----------
        level : str
            Analysis level (precursor, protein, gene)
        section : str
            Section name (var, obs, pr_obs, x, mod_obs, optional)

        Returns:
        --------
        List[str]
            List of column names for that section
        """
        if level not in self.config['levels']:
            raise ValueError(
                f"Level '{level}' not found. Available: {list(self.config['levels'].keys())}"
            )

        level_config = self.config['levels'][level]

        if section not in level_config:
            raise ValueError(
                f"Section '{section}' not found in level '{level}'. "
                f"Available: {list(level_config.keys())}"
            )

        section_data = level_config[section]
        if section_data is None:
            return []

        return section_data if isinstance(section_data, list) else []

    def check_available_levels(
        self,
        filepath: str,
        sections: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, List[str]]]:
        """
        Check which levels can be loaded from a file based on available columns.

        This is much more efficient than trying to load each level, as it only
        reads the header line instead of loading the entire TSV file.

        Parameters:
        -----------
        filepath : str
            Path to DIA-NN report file
        sections : List[str], optional
            Specific sections to check

        Returns:
        --------
        Dict[str, Dict[str, List[str]]]
            Dictionary with level names as keys, each containing:
            - 'available': True if all required columns present, False otherwise
            - 'missing_columns': List of missing column names
            - 'present_columns': List of present required columns
        """
        # Read just the header line
        with open(filepath, 'r') as f:
            header = f.readline().strip().split('\t')

        available_columns = set(header)
        results = {}

        for level in self.config['levels'].keys():
            # Determine which sections to check
            if sections is None:
                check_sections = [s for s in ['var_name', 'obs_name', 'x', 'var', 'obs', 'layers', 'pr_obs']
                           if s in self.config['levels'][level]]
            else:
                check_sections = sections

            # Get required columns for this level
            required_cols_raw = self.get_columns(level, check_sections)
            required_cols = list(dict.fromkeys(required_cols_raw))  # Remove duplicates

            # Check which are present
            required_set = set(required_cols)
            present = required_set & available_columns
            missing = required_set - available_columns

            results[level] = {
                'available': len(missing) == 0,
                'missing_columns': sorted(list(missing)),
                'present_columns': sorted(list(present)),
                'total_required': len(required_cols)
            }

        return results

    def load_to_df(
        self,
        filepath: str,
        level: str,
        sections: Optional[List[str]] = None,
        strict: bool = False,
        search_type: str = 'bps'
    ) -> pd.DataFrame:
        """
        Load DIA-NN data with column selection based on level.

        Parameters:
        -----------
        filepath : str
            Path to DIA-NN report file
        level : str
            Analysis level (precursor, protein, gene)
        sections : List[str], optional
            Specific sections to include (var_name, obs_name, x, var, obs, layers)
            If None, includes all sections except layers (unless include_layers=True)
        include_layers : bool
            If True, include layer columns
        strict : bool
            If True, raise error if expected columns are missing

        Returns:
        --------
        pd.DataFrame
            DataFrame with selected columns
        """

        # Determine which sections to load
        if sections is None:
            sections = [s for s in ['var_name', 'obs_name', 'x', 'var', 'obs', 'layers', 'pr_obs']
                       if s in self.config['levels'][level]]

        # Get expected columns and remove duplicates while preserving order
        expected_cols_raw = self.get_columns(level, sections)
        # Use dict.fromkeys() to preserve order while removing duplicates
        expected_cols = list(dict.fromkeys(expected_cols_raw))

        # Load full dataframe
        df = pd.read_csv(filepath, sep='\t')

        # Check for missing columns
        missing_cols = set(expected_cols) - set(df.columns)

        if missing_cols:
            msg = f"Missing columns for level '{level}': {missing_cols}"
            if strict:
                raise ValueError(msg)
            else:
                logger.info(msg)

        # Select available columns from expected list (no duplicates)
        available_cols = [col for col in expected_cols if col in df.columns]

        logger.info(f"Loaded {len(df)} rows with {len(available_cols)}/{len(expected_cols)} columns for level '{level}'")

        if missing_cols:
            logger.info(f"Missing columns: {missing_cols}")

        result = df.loc[:, available_cols]

        # return grouped/agg table for protein level + check to make sure collapsed values are redundant
        if level in ['protein', 'gene']:
            level_config = self.config['levels'][level]
            obs = level_config['obs']
            var = level_config['var']

            # check if any var+obs columns have all NaN values -> if so, exclude from grouping
            valid_groupby_cols = result[var+obs].dropna(axis=1, how='all').columns.to_list()
            
            # TODO: add pr_obs in the yaml
            # TODO: make more formalized way to handle missing genes
            if level == 'protein':
                pr_obs = level_config['pr_obs']
            
            else:
                protein_config = self.config['levels']['protein']
                nan_genes = df[obs[0]].isna()
                protein_gene_sub = df[protein_config.get('obs', [])[0]][nan_genes] + '_P'
                df.loc[nan_genes, obs[0]] = protein_gene_sub

            # Ensure pr_obs columns are not in groupby (they should be aggregated, not grouped by)
            valid_groupby_cols = [col for col in valid_groupby_cols if col not in pr_obs]

            # Get columns that need aggregation (everything not in groupby)
            cols_to_agg = [col for col in result.columns if col not in valid_groupby_cols + pr_obs]

            #TODO: count number of peptides per protein
            #TODO: get sequences per protein (and mods?) -> calculate protein coverage

            def check_unique(x):
                unique_vals = x.unique()
                if len(unique_vals) > 1:
                    warnings.warn(f"Non-unique values found during aggregation: {unique_vals}")
                    return pd.Series(unique_vals).astype(str).str.join(';')
                return unique_vals[0] if len(unique_vals) == 1 else ''

            # Build named aggregation dictionary
            agg_dict = {}
            for obs in pr_obs:
                agg_dict[f'Num_{obs}'] = (obs, 'count')
                agg_dict[f'Nunique_{obs}'] = (obs, 'nunique')
                agg_dict[f'All_{obs}'] = (obs, list)

            # Add aggregation for remaining columns (those not in pr_obs)
            for col in cols_to_agg:
                agg_dict[col] = (col, check_unique)  # type: ignore

            #keep multindex to use for pivot table later, removes need to respecify columns
            result = result.groupby(valid_groupby_cols).agg(**agg_dict).reset_index()

        if search_type == 'fragpipe':
            result['search_type'] = 'fragpipe'
            result['Run'] = result['File.Name'].str.extract(r'.+\/(.+)\.d$', expand=False)
        else:
            result['search_type'] = 'bps'
            # result = result.drop(columns=pr_obs)

        return result # type: ignore
    
    def load_to_adata(
        self,
        filepath: str,
        level: str,
        sections: Optional[List[str]] = None,
        strict: bool = False,
        output_path: Optional[str] = None,
        mk_dir: bool = True,
        search_type: str = 'bps'
    ) -> ad.AnnData:
        """
        Load DIA-NN data with column selection based on level into an AnnData object.

        Parameters:
        -----------
        filepath : str
            Path to DIA-NN report file
        level : str
            Analysis level (precursor, protein, gene)
        sections : List[str], optional
            Specific sections to include (var, obs, pr_obs, x, mod_obs, optional)
            If None, includes all sections
        include_optional : bool
            If True, include optional columns if they exist
        strictly_uniquevar : bool
            If True, raise error designated var names are not all unique
            If False, make var names unique by appending indices and raise warning

        Returns:
        --------
        anndata.AnnData
            AnnData object with selected columns
        """

        df = self.load_to_df(
            filepath,
            level,
            sections,
            strict, 
            search_type=search_type
        )

        # Create AnnData object
        level_config = self.config['levels'][level]

        # Smart selection of obs_name: use first obs column that exists and has unique values
        obs_name = None
        obs_candidates = level_config.get('obs', [])

        # Ensure obs_candidates is always a list of strings
        # Handle both single string values and list values from YAML
        if isinstance(obs_candidates, str):
            # Single string value - wrap in list
            obs_candidates = [obs_candidates]
        elif not isinstance(obs_candidates, list):
            # Some other type - convert to list
            obs_candidates = [obs_candidates]

        # First try to find a unique column
        for candidate in obs_candidates:
            if candidate in df.columns:
                # Check if values are unique

                if not df[candidate].isna().any():
                    obs_name = candidate
                    logger.info(f"Using '{obs_name}' as obs_name")
                    break

                else:
                    logger.info(f"{candidate} is contains NaN")

        # Smart selection of var_name: use first var column that exists
        var_name = None
        var_candidates = level_config.get('var', [])
        var_candidates += ['search_type']

        # Ensure var_candidates is always a list of strings
        # Handle both single string values and list values from YAML
        if isinstance(var_candidates, str):
            # Single string value - wrap in list
            var_candidates = [var_candidates]
        elif not isinstance(var_candidates, list):
            # Some other type - convert to list
            var_candidates = [var_candidates]

        for candidate in var_candidates:
            if candidate in df.columns:
                # Warn if var_name is not unique within sample
                if not df[candidate].isna().any():
                    var_name = candidate
                    logger.info(f"Using '{var_name}' as var_name")
                    break
                else:
                    logger.info(f"{candidate} is fully NaN")

        if var_name is None:
            raise KeyError(
                f"Cannot create AnnData for level '{level}': "
                f"no valid var column found. Tried: {var_candidates}"
            )

        # Smart selection of x: try each layer column until one works
        x_candidates = level_config.get('layers', [])

        # Ensure x_candidates is always a list of strings
        if isinstance(x_candidates, str):
            x_candidates = [x_candidates]
        elif not isinstance(x_candidates, list):
            x_candidates = [x_candidates]

        # Get obs columns for pivot index (all columns in obs section)
        obs_cols = level_config.get('obs', [obs_name])

        # Ensure obs_cols is always a list of strings
        if isinstance(obs_cols, str):
            obs_cols = [obs_cols]
        elif not isinstance(obs_cols, list):
            obs_cols = [obs_cols]

        # # Filter to only obs columns that actually exist in df
        available_obs_cols = [col for col in obs_cols if col in df.columns]

        df_for_pivot = df
        # Try each quantification column until one works
        pivot_df = None
        x_col = None
        last_error = None

        for candidate in x_candidates:
            if candidate not in df_for_pivot.columns:
                continue

            # Check if not all empty/null
            if df_for_pivot[candidate].isna().all():
                continue

            try:
                logger.info(f"Using '{candidate}' as x (quantification column)")
                pivot_df = df_for_pivot.pivot(index=available_obs_cols,
                                              columns=var_name,
                                              values=candidate)
                x_col = candidate
                break  # Success! Use this column
            except (ValueError, KeyError) as e:
                last_error = e
                logger.warning(f"Failed to pivot with '{candidate}': {type(e).__name__}")
                continue

        if pivot_df is None or x_col is None:
            error_msg = (
                f"Cannot create AnnData for level '{level}': "
                f"no valid quantification column found. Tried: {x_candidates[:5]}..."
            )
            if last_error:
                error_msg += f"\nLast error: {last_error}"
            raise KeyError(error_msg)

        # Extract var dataframe from pivot columns
        # If pivot has multiindex columns, get the var_name level
        if isinstance(pivot_df.columns, pd.MultiIndex):
            # Find which level has var_name
            var_level_idx = None
            for i, name in enumerate(pivot_df.columns.names):
                if name == var_name:
                    var_level_idx = i
                    break
            if var_level_idx is not None:
                var_df = pivot_df.columns.get_level_values(var_level_idx).to_frame(index=False, name=var_name)
            else:
                # Use last level as fallback
                var_df = pivot_df.columns.levels[-1].to_frame(name=var_name)
        else:
            # Single level columns
            var_df = pivot_df.columns.to_frame(index=False, name=var_name)

        adata = ad.AnnData(X = pivot_df.values,
                   obs = pivot_df.index.to_frame().reset_index(drop=True),
                   var = var_df.reset_index(drop=True))

        # Check and set observation names
        temp_obs_name = adata.obs[obs_name]

        # Set obs_names first (explicitly convert to string to avoid anndata warning)
        adata.obs_names = temp_obs_name.astype(str)

        # Then make unique if needed using anndata's built-in method
        if not adata.obs_names.is_unique:
            msg = f"Non-unique observation names detected. {adata.n_obs} observations but only {temp_obs_name.nunique()} unique names."
            if strict:
                raise ValueError(msg)
            else:
                warnings.warn(msg)
                # Save original names
                adata.obs[f'{obs_name}_original'] = temp_obs_name.values
                # Use anndata's method to make unique
                adata.obs_names_make_unique()
                logger.info("Obs names made unique using anndata method.")

        # Explicitly convert var_names to string to avoid anndata warning
        adata.var_names = adata.var[var_name].astype(str)

        # not using layers in the config to account for additional processing that can added extra layers
        # Only use columns that actually exist
        var_cols_available = [c for c in level_config.get('var', []) if c in df_for_pivot.columns]
        obs_cols_available = [c for c in level_config.get('obs', []) if c in df_for_pivot.columns]

        layers = df_for_pivot.columns[~df_for_pivot.columns.isin(var_cols_available + obs_cols_available)]

        for l in layers:
            pivot_df = df_for_pivot.pivot(index=available_obs_cols,
                                          columns=var_name,
                                          values=l)
            
            pivot_df.reindex(index=adata.obs_names,
                                               columns=adata.var_names,
                                               fill_value=np.nan)

            adata.layers[l] = pivot_df.values
        # TODO: make it possible to save to h5ad
        # if output_path:
        #     output_dir = os.path.dirname(output_path)
        #     if output_dir and not os.path.exists(output_dir):
        #         if mk_dir:
        #             os.makedirs(output_dir, exist_ok=True)
        #             print(f"Created directory: {output_dir}/{level}")
        #         else:
        #             raise FileNotFoundError(f"Directory does not exist: {output_dir}. Set mk_dir=True to create it.")
        #     adata.write_h5ad(f'{output_path}/{level}_report.h5ad')
        #     print(f"AnnData object saved to {output_path}/{level}_report.h5ad")
            
        return adata



# Usage example
if __name__ == "__main__":
    loader = DiannLoader("diann_columns.yaml")

    # Example 1: Load precursor-level data with all sections including layers
    df_precursor = loader.load_to_df(
        "diann_report.tsv",
        level="precursor",
    )

    # Example 2: Load protein-level data without layers
    df_protein = loader.load_to_df(
        "diann_report.tsv",
        level="protein"
    )

    # Example 3: Load only specific sections for precursor level
    df_precursor_minimal = loader.load_to_df(
        "diann_report.tsv",
        level="precursor",
        sections=["var", "obs", "x"],
        strict=True
    )

    # Example 4: Get column names for a specific level
    print("\nAll columns for precursor level:")
    print(loader.get_columns("precursor"))

    # Example 5: Get columns for a specific section
    print("\nLayer columns for precursor level:")
    print(loader.get_section_columns("precursor", "layers"))