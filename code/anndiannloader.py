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
            missing = '\n      * '.join(missing_cols)
            msg = f"    Missing columns for level '{level}':\n      * {missing}"
            if strict:
                raise ValueError(msg)
            else:
                logger.info(msg)

        # Select available columns from expected list (no duplicates)
        available_cols = [col for col in expected_cols if col in df.columns]

        logger.info(f"Loaded {len(df)} rows with {len(available_cols)}/{len(expected_cols)} columns for level '{level}'")

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
            result['Run'] = result['File.Name'].apply(lambda x: os.path.splitext(os.path.basename(x))[0])
            result['hystar_index'] = result['Run'].str.extract(r'.+_(\d+)', expand=False)

        elif search_type == 'bps':
            result['hystar_index'] = result['File.Name'].str.extract(r'.+_(\d+)', expand=False)

        result['search_type'] = search_type
        return result # type: ignore

    def get_valid_cols(self, df, level_config, level):
        """Helper method to get valid columns for a given level."""
        cols = level_config.get(level, [])
        if isinstance(cols, str):
            # Single string value - wrap in list
            cols = [cols]
        elif not isinstance(cols, list):
            # Some other type - convert to list
            cols = [cols]
        
        cols = [c for c in cols if c in df.columns]
        
        if level == 'layers':
            cols_without_nan = ~df.loc[:, cols].isna().all()
        else:
            cols_without_nan = ~df.loc[:, cols].isna().any()

        valid_cols = [col for col, is_valid in zip(cols, cols_without_nan) if is_valid]

        if len(valid_cols) == 0:
            raise ValueError(f"No {level} columns found without NaN values. Tried: {cols}")

        main_col = valid_cols[0]

        return valid_cols, main_col
    
    def load_to_adata(
        self,
        data: str | pd.DataFrame,
        level: str,
        search_type: str = 'bps',
        sections: Optional[List[str]] = None,
        strict: bool = False,
        output_path: Optional[str] = None,
        mk_dir: bool = True
    ) -> ad.AnnData:
        """
        Load DIA-NN data with column selection based on level into an AnnData object.

        Parameters:
        -----------
        data : str | pd.DataFrame
            Path to DIA-NN report file or a DataFrame
        level : str
            Analysis level (precursor, protein, gene)
        sections : List[str], optional
            Specific sections to include (var, obs, pr_obs, x, mod_obs, optional)
            If None, includes all sections
        strict : bool
            If True, raise error if expected columns are missing
        output_path : str, optional
            Path to save the AnnData object
        mk_dir : bool
            If True, create output directory if it doesn't exist

        Returns:
        --------
        anndata.AnnData
            AnnData object with selected columns
        """
        if isinstance(data, str):
            df = self.load_to_df(
                    data,
                    level,
                    sections,
                    strict, 
                    search_type=search_type
            )
        elif isinstance(data, pd.DataFrame):
            df = data
        else:
            raise ValueError(f"Data must be either a file path (str) or pandas DataFrame, got {type(data)}")
            
        # Create AnnData object
        level_config = self.config['levels'][level]

        var, var_name = self.get_valid_cols(df, level_config, 'var')
        var += ['search_type', 'hystar_index']

        obs, obs_name = self.get_valid_cols(df, level_config, 'obs')

        layers, x = self.get_valid_cols(df, level_config, 'layers')

        logger.info(f"Using '{x}' as X layer")

        #obs will not work properly if some aggregation is needed
        pivot_df = df.pivot(index=obs_name,
                            columns=var,
                            values=layers)

        # # Convert MultiIndex columns to var DataFrame
        if isinstance(pivot_df.columns, pd.MultiIndex):
            # MultiIndex case: convert to DataFrame with column names from var list
            var_df = pivot_df.columns[pivot_df.columns.get_level_values(0) == x] # repeats for each layer
            var_df = var_df.to_frame(index=False).drop(columns=0)
            var_df.columns = var  # Name the columns according to var list
        else:
            # Single index case
            var_df = pivot_df.columns.to_frame(index=False)

        # handle obs separately since there is a chance for non-redundant values for some of the obs with the same obs_name
        obs_df = df.loc[:, obs]
        obs_df = obs_df.groupby(obs_name).agg(lambda x: ';'.join(list(set(';'.join(x.astype(str)).split(';')))))
        obs_df = obs_df.reindex(index=pivot_df.index, fill_value=np.nan)
        obs_df[obs_name] = obs_df.index

        adata = ad.AnnData(X=pivot_df.loc[:, x].values,
                           obs=obs_df,
                           var=var_df.set_index(var_name, drop=False),
                           layers = {metric: pivot_df.loc[:, metric].values for metric in layers}
        )

        # Then make unique if needed using anndata's built-in method
        if not adata.obs_names.is_unique:
            msg = f"Non-unique observation names detected. {adata.n_obs} observations but only {adata.obs[obs_name].nunique()} unique names."
            if strict:
                raise ValueError(msg)
            else:
                warnings.warn(msg)
                # Save original names
                adata.obs[f'{obs_name}_original'] = adata.obs[obs_name].values
                # Use anndata's method to make unique
                adata.obs_names_make_unique()
                logger.info("Obs names made unique using anndata method.")

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