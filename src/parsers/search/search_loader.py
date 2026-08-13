import pandas as pd
import yaml
from typing import List, Optional, Dict, Union
import warnings
import anndata as ad
import numpy as np
import os
import logging
from scipy.sparse import csr_matrix


# Set up logger for this module
logger = logging.getLogger(__name__)

class SearchLoader:
    def __init__(self, container: str = 'bps', engine: str = 'diann', config_path: Optional[str] = None, additional_columns: Optional[Dict[str, Dict]] = None, search_type: Optional[str] = None):
        """Initialize with DIA-NN/Spectronaut column configuration file.
        
        Parameters:
        -----------
        container : str
            Data container type ('bps', 'fragpipe', 'diann')
        engine : str
            Search engine type ('diann', 'spectronaut')
        config_path : str, optional
            Path to YAML configuration file
        additional_columns : Dict[str, Dict], optional
            Dictionary mapping custom column names to their configuration:
            {
                'column_name': {
                    'storage': 'var'|'obs'|'layer',  # Where to store in AnnData
                    'levels': ['precursor', 'protein'],  # Which levels it applies to (None = all)
                    'section': 'identification'|'quantification'|'optional'  # Which section
                }
            }
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

        # If config_path is relative, resolve it relative to this module's directory
        if config_path is None:
            if engine == 'diann':
                # Use diann261 yaml for diann+diann, regular diann yaml for others
                if container == 'diann':
                    config_path = "diann261_columns.yaml"
                else:
                    config_path = "diann_columns.yaml"
            elif engine == 'spectronaut':
                config_path = "spnt_columns.yaml"
            else:
                raise ValueError(f"Unknown engine '{engine}'. Must be 'diann' or 'spectronaut'.")

        if not os.path.isabs(config_path):
            module_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(module_dir, config_path)

        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Store additional custom columns configuration
        self.additional_columns = additional_columns or {}
    
    def add_column_config(self, column_name: str, storage: str, levels: Optional[List[str]] = None, section: str = 'optional'):
        """Add or update a custom column configuration.
        
        Parameters:
        -----------
        column_name : str
            Name of the custom column
        storage : str
            Where to store in AnnData: 'var', 'obs', or 'layer'
        levels : List[str], optional
            Which levels this column applies to (None = all levels)
        section : str
            Which section to include the column in (default: 'optional')
        """
        if storage not in ['var', 'obs', 'layer']:
            raise ValueError(f"storage must be 'var', 'obs', or 'layer', got '{storage}'")
        
        self.additional_columns[column_name] = {
            'storage': storage,
            'levels': levels,
            'section': section
        }
    
    def remove_column_config(self, column_name: str):
        """Remove a custom column configuration."""
        if column_name in self.additional_columns:
            del self.additional_columns[column_name]
    
    def get_additional_columns_for_level(self, level: str, section: Optional[str] = None) -> List[str]:
        """Get list of additional columns applicable to a specific level and section.
        
        Parameters:
        -----------
        level : str
            The level to get columns for
        section : str, optional
            Filter by section (if None, returns all)
        
        Returns:
        --------
        List[str]
            List of additional column names
        """
        columns = []
        for col_name, config in self.additional_columns.items():
            # Check if level applies
            if config.get('levels') is None or level in config.get('levels', []):
                # Check if section applies
                if section is None or config.get('section') == section:
                    columns.append(col_name)
        return columns
    
    def add_column_to_yaml_config(self, level: str, section: str, column_name: str):
        """Add a column to a specific level and section in the YAML config.
        
        Parameters:
        -----------
        level : str
            The level to add the column to (e.g., 'precursor', 'protein')
        section : str
            The section within the level (e.g., 'var', 'obs', 'x', 'layers')
        column_name : str
            Name of the column to add
        """
        if 'levels' not in self.config:
            self.config['levels'] = {}
        
        if level not in self.config['levels']:
            self.config['levels'][level] = {}
        
        if section not in self.config['levels'][level]:
            self.config['levels'][level][section] = []
        
        # Ensure section is a list
        if not isinstance(self.config['levels'][level][section], list):
            self.config['levels'][level][section] = []
        
        # Add column if not already present
        if column_name not in self.config['levels'][level][section]:
            self.config['levels'][level][section].append(column_name)
    
    def remove_column_from_yaml_config(self, level: str, section: str, column_name: str):
        """Remove a column from a specific level and section in the YAML config.
        
        Parameters:
        -----------
        level : str
            The level to remove the column from
        section : str
            The section within the level
        column_name : str
            Name of the column to remove
        """
        if (level in self.config.get('levels', {}) and 
            section in self.config['levels'][level] and
            isinstance(self.config['levels'][level][section], list)):
            
            if column_name in self.config['levels'][level][section]:
                self.config['levels'][level][section].remove(column_name)
    
    def add_level_to_yaml_config(self, level: str, level_config: Optional[Dict] = None):
        """Add a new level to the YAML config.
        
        Parameters:
        -----------
        level : str
            Name of the level to add
        level_config : Dict, optional
            Configuration for the level. If None, creates empty level with standard sections.
        """
        if 'levels' not in self.config:
            self.config['levels'] = {}
        
        if level not in self.config['levels']:
            if level_config is None:
                # Create default structure
                self.config['levels'][level] = {
                    'var_name': [],
                    'obs_name': [],
                    'var': [],
                    'obs': [],
                    'x': [],
                    'layers': [],
                    'optional': []
                }
            else:
                self.config['levels'][level] = level_config
    
    def remove_level_from_yaml_config(self, level: str):
        """Remove a level from the YAML config.
        
        Parameters:
        -----------
        level : str
            Name of the level to remove
        """
        if level in self.config.get('levels', {}):
            del self.config['levels'][level]
    
    def add_section_to_level(self, level: str, section: str, columns: Optional[List[str]] = None):
        """Add a section to a level in the YAML config.
        
        Parameters:
        -----------
        level : str
            The level to add the section to
        section : str
            Name of the section to add
        columns : List[str], optional
            Initial columns for the section (default: empty list)
        """
        if 'levels' not in self.config:
            self.config['levels'] = {}
        
        if level not in self.config['levels']:
            raise ValueError(f"Level '{level}' not found in config")
        
        if section not in self.config['levels'][level]:
            self.config['levels'][level][section] = columns if columns is not None else []
    
    def remove_section_from_level(self, level: str, section: str):
        """Remove a section from a level in the YAML config.
        
        Parameters:
        -----------
        level : str
            The level to remove the section from
        section : str
            Name of the section to remove
        """
        if (level in self.config.get('levels', {}) and 
            section in self.config['levels'][level]):
            del self.config['levels'][level][section]
    
    def save_yaml_config(self, output_path: str):
        """Save the current config to a YAML file.
        
        Parameters:
        -----------
        output_path : str
            Path where to save the YAML configuration
        """
        with open(output_path, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)
            
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
                check_sections = [s for s in ['var_name', 'obs_name', 'x', 'var', 'obs', 'layers', 'pr_obs', 'pg_obs']
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
    
    def load_search(
            self, 
            filepath: str
    ) -> pd.DataFrame:
        """
        Load search data from a file into a DataFrame.

        Parameters:
        -----------
        filepath : str
            Path to search data file

        Returns:
        --------
        pd.DataFrame
            DataFrame containing the search data
            """
        # Determine file format by extension for diann engine (supports both parquet and tsv)
        if self.engine == 'diann':
            if filepath.endswith('.parquet'):
                df = pd.read_parquet(filepath)
            else:
                df = pd.read_csv(filepath, sep='\t')
        elif self.engine == 'spectronaut':
            df = pd.read_parquet(filepath)
        return df

    def load_to_level_df(
        self,
        data: Union[str, pd.DataFrame],
        level: str,
        sections: Optional[List[str]] = None,
        strict: bool = False,
        source_path: Optional[str] = None
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
        strict : bool
            If True, raise error if expected columns are missing
        source_path : str, optional
            Original source path (e.g., zip file path) to track in metadata.
            If None, uses filepath as source.

        Returns:
        --------
        pd.DataFrame
            DataFrame with selected columns
        """
        # Load full dataframe
        if isinstance(data, str):
            df = self.load_search(data)
        elif isinstance(data, pd.DataFrame):
            df = data.copy()
        else:
            raise ValueError(f"Data must be either a file path (str) or pandas DataFrame, got {type(data)}")

        if level == 'none':
            return df

        # Determine which sections to load
        if sections is None:
            sections = [s for s in ['var_name', 'obs_name', 'x', 'var', 'obs', 'layers', 'pr_obs', 'pg_obs']
                       if s in self.config['levels'][level]]

        # Get expected columns and remove duplicates while preserving order
        expected_cols_raw = self.get_columns(level, sections)
        # Use dict.fromkeys() to preserve order while removing duplicates
        expected_cols = list(dict.fromkeys(expected_cols_raw))

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
            
            # Add search_path after aggregation to avoid it being included in aggregation warnings
            if source_path:
                result['search_path'] = source_path
            elif isinstance(data, str):
                result['search_path'] = os.path.abspath(data)
            else:
                result['search_path'] = ''
        else:
            # For non-protein/gene levels, add search_path normally
            if source_path:
                result['search_path'] = source_path
            elif isinstance(data, str):
                result['search_path'] = os.path.abspath(data)
            else:
                result['search_path'] = ''

        # Add run and index information
        if self.container == 'fragpipe' and self.engine == 'diann':
            if 'File.Name' in result.columns:
                result['Run'] = result['File.Name'].apply(lambda x: os.path.splitext(os.path.basename(x))[0])
                result['hystar_index'] = result['Run'].str.extract(r'.+_(\d+)', expand=False)

        elif self.container == 'diann' and self.engine == 'diann':
            # Same behavior as fragpipe+diann
            if 'File.Name' in result.columns:
                result['Run'] = result['File.Name'].apply(lambda x: os.path.splitext(os.path.basename(x))[0])
                result['hystar_index'] = result['Run'].str.extract(r'.+_(\d+)', expand=False)

        elif self.container == 'bps' and self.engine == 'diann':
            if 'File.Name' in result.columns:
                result['hystar_index'] = result['File.Name'].str.extract(r'.+_(\d+)', expand=False)
        elif self.container == 'bps' and self.engine == 'spectronaut':
            if 'sample_name' in result.columns:
                result['hystar_index'] = result['sample_name'].str.extract(r'.+_(\d+)', expand=False)

        result['search_type'] = self.search_type
        result['container'] = self.container
        result['engine'] = self.engine
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
        
        if len(cols) == 0:
            # No columns found at all, return empty list and None
            return [], None
        
        if level == 'layers':
            cols_without_nan = ~df.loc[:, cols].isna().all()
        else:
            cols_without_nan = ~df.loc[:, cols].isna().any()

        valid_cols = [col for col, is_valid in zip(cols, cols_without_nan) if is_valid]

        if len(valid_cols) == 0:
            # No non-NaN columns found, but columns exist - return the first available column
            logger.warning(f"No {level} columns found without NaN values. Using first available: {cols[0]}")
            return [cols[0]], cols[0]

        main_col = valid_cols[0]

        return valid_cols, main_col
    
    def load_to_adata(
        self,
        data: str | pd.DataFrame,
        level: str,
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
            df = self.load_to_level_df(
                    data,
                    level,
                    sections,
                    strict
            )

        elif isinstance(data, pd.DataFrame):
            df = data
        else:
            raise ValueError(f"Data must be either a file path (str) or pandas DataFrame, got {type(data)}")
            
        # Create AnnData object
        level_config = self.config['levels'][level]

        var, var_name = self.get_valid_cols(df, level_config, 'var')
        
        # Handle case where no var columns found
        if not var or var_name is None:
            logger.warning(f"No var columns found for level '{level}', using index as var_name")
            # Create a default var column if none exist
            df['_default_var'] = df.index.astype(str)
            var = ['_default_var']
            var_name = '_default_var'
        
        # Only add these columns if they exist in the DataFrame
        additional_vars = []
        if 'search_path' in df.columns:
            additional_vars.append('search_path')
        if 'search_type' in df.columns:
            additional_vars.append('search_type')
        if 'hystar_index' in df.columns:
            additional_vars.append('hystar_index')
        var += additional_vars

        obs, obs_name = self.get_valid_cols(df, level_config, 'obs')
        
        # Handle case where no obs columns found
        if not obs or obs_name is None:
            logger.warning(f"No obs columns found for level '{level}', cannot create AnnData object")
            raise ValueError(f"No obs columns found for level '{level}'. Cannot create AnnData without observation identifiers.")


        # Add pr_obs and pg_obs as layers if present in config
        pr_obs_layers = []
        pg_obs_layers = []
        try:
            pr_obs_result, _ = self.get_valid_cols(df, level_config, 'pr_obs')
            if pr_obs_result:
                pr_obs_layers = pr_obs_result
        except Exception:
            pass
        try:
            pg_obs_result, _ = self.get_valid_cols(df, level_config, 'pg_obs')
            if pg_obs_result:
                pg_obs_layers = pg_obs_result
        except Exception:
            pass

        layers, x = self.get_valid_cols(df, level_config, 'layers')
        
        # Handle case where no layers found
        if not layers or x is None:
            logger.warning(f"No layer columns found for level '{level}', cannot create AnnData object")
            raise ValueError(f"No layer columns found for level '{level}'. Cannot create AnnData without data layers.")
        extra_layers = pr_obs_layers + pg_obs_layers
        if extra_layers:
            layers += extra_layers
            logger.info(f"Using '{x}' as X layer and additional layers: {extra_layers}")
        else:
            logger.info(f"Using '{x}' as X layer (no pr_obs/pg_obs layers found)")

        # Create unique IDs to handle duplicates by preserving all data instead of aggregating
        df_copy = df.copy()
        
        # Handle duplicate var_names from different search_paths
        # If same var_name exists with different search_paths, make var_names unique
        if 'search_path' in df_copy.columns and var_name in df_copy.columns:
            # Check if there are duplicate var_names with different search_paths
            var_search_groups = df_copy.groupby(var_name)['search_path'].nunique()
            has_multiple_sources = (var_search_groups > 1).any()
            
            # Also check if there are multiple search paths in the dataset
            multiple_search_paths = df_copy['search_path'].nunique() > 1
            
            if has_multiple_sources or multiple_search_paths:
                # Create a search_path_index for each unique search_path
                unique_search_paths = df_copy['search_path'].unique()
                search_path_to_index = {path: idx for idx, path in enumerate(unique_search_paths)}
                df_copy['search_path_index'] = df_copy['search_path'].map(search_path_to_index)
                
                # Make var_names unique by appending search_path_index
                df_copy[f'{var_name}_unique'] = df_copy[var_name].astype(str) + '_sp' + df_copy['search_path_index'].astype(str)
                
                # Replace var_name in the var list with the unique version
                var_name_idx = var.index(var_name)
                var[var_name_idx] = f'{var_name}_unique'
                var_name = f'{var_name}_unique'
                
                # Add search_path_index to var list if not already there
                if 'search_path_index' not in var:
                    var.append('search_path_index')
                
                logger.info(f"Found {len(unique_search_paths)} unique search paths. Created search_path_index and unique var_names.")
        
        # Convert columns to strings to ensure they are hashable for groupby operations
        groupby_cols = obs + var
        for col in groupby_cols:
            if col in df_copy.columns:
                df_copy[col] = df_copy[col].astype(str)
        
        # Create unique identifier based on obs+var combinations to avoid duplicates in pivot
        if df_copy[var + [obs_name]].duplicated().any():
            if df_copy.loc[:, groupby_cols].duplicated().any():
            # Create a base unique string from obs columns
                base_unique = df_copy[obs].astype(str).apply(lambda x: '_'.join(x), axis=1)
                # Add a counter for each duplicate group
                dup_counter = df_copy.groupby(base_unique).cumcount().astype(str)
                df_copy[f'{obs_name}_unique'] = base_unique + '_' + dup_counter
            else:
                df_copy[f'{obs_name}_unique'] = df_copy[obs].astype(str).apply(lambda x: '_'.join(x), axis=1)
            obs_name = f'{obs_name}_unique'
            obs.append(obs_name)
    
        pivot_df = df_copy.pivot(index=obs_name,
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
        obs_df = df_copy.loc[:, obs]
        obs_df = obs_df.set_index(obs_name)
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