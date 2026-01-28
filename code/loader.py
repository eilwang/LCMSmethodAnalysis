from ctypes.util import test
import pandas as pd
import yaml
from typing import List, Optional, Dict
import warnings
import anndata as ad # pyright: ignore[reportMissingImports]
import numpy as np

class DiannLoader:
    def __init__(self, config_path: str = "diann_columns.yaml"):
        """Initialize with DIA-NN column configuration file."""
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
    
    def load_to_df(
        self,
        filepath: str,
        level: str,
        sections: Optional[List[str]] = None,
        strict: bool = False
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
                warnings.warn(msg)

        # Select available columns from expected list (no duplicates)
        available_cols = [col for col in expected_cols if col in df.columns]

        print(f"Loaded {len(df)} rows with {len(available_cols)}/{len(expected_cols)} columns for level '{level}'")

        if missing_cols:
            print(f"Missing columns: {missing_cols}")

        result = df.loc[:, available_cols]

        # return grouped/agg table for protein level + check to make sure collapsed values are redundant
        if level == 'protein':
            level_config = self.config['levels'][level]
            obs = level_config['obs']
            var = level_config['var']

            # check if any var+obs columns have all NaN values -> if so, exclude from grouping
            valid_groupby_cols = result[var+obs].dropna(axis=1, how='all').columns.to_list()

            pr_obs = level_config['pr_obs']

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

            # result = result.drop(columns=pr_obs)

        return result # type: ignore
    
    def load_to_adata(
        self,
        filepath: str,
        level: str,
        sections: Optional[List[str]] = None,
        include_optional: bool = True,
        strict: bool = False,
        strictly_uniquevar: bool = True
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
            strict
        )

        # Create AnnData object
        level_config = self.config['levels'][level]

        var_name = level_config['var_name'][0]
        obs_name = level_config['obs_name'][0]

        pivot_df = df.pivot(index=level_config['obs'],
                            columns=var_name, 
                            values=level_config['x'])

        adata = ad.AnnData(X = pivot_df.values,
                   obs = pivot_df.index.to_frame().reset_index(drop=True),
                   var = pivot_df.columns.levels[1].to_frame()) # type: ignore

        # temp_obs_name = adata.obs[obs_name_cols[0]]
        temp_obs_name = adata.obs[obs_name]

        if temp_obs_name.nunique() != adata.n_obs:
            msg = f"Non-unique observation names detected. {adata.n_obs} observations but only {temp_obs_name.nunique()} unique names."
            if strict:
                if temp_obs_name.nunique() != adata.n_obs:
                    msg = f"Non-unique observation names detected. {adata.n_obs} observations but only {temp_obs_name.nunique()} unique names."
                    raise ValueError(msg)
            else:
                warnings.warn(msg)
                adata.obs_names_make_unique()
                s
                print("Obs names made unique by appending indices.")
                print(adata.obs_names[~adata.obs_names.isin(temp_obs_name)])

        adata.obs_names = adata.obs[obs_name]
        adata.var_names = adata.var[var_name]

        # not using layers in the config to account for additional processing that can added extra layers

        layers = df.columns[~df.columns.isin(level_config['var'] + level_config['obs'])]

        for l in layers:
            pivot_df = df.pivot(index=level_config['obs'], 
                                columns=var_name,
                                values=l)
            
            adata.layers[l] = pivot_df.reindex(index=adata.obs_names,
                                               columns=adata.var_names, 
                                               fill_value=np.nan).values

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