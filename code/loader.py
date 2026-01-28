import pandas as pd
import yaml
from typing import List, Optional, Dict
import warnings

class DataLoader:
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize with config file."""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
    
    def get_columns(self, level: str, include_optional: bool = True) -> List[str]:
        """Get column list for specified level."""
        if level not in self.config['levels']:
            raise ValueError(f"Level '{level}' not found. Available: {list(self.config['levels'].keys())}")
        
        level_config = self.config['levels'][level]
        cols = level_config['required'].copy()
        
        if include_optional:
            cols.extend(level_config['optional'])
        
        return cols
    
    def load_data(
        self, 
        filepath: str, 
        level: str,
        source_format: Optional[str] = None,
        include_optional: bool = True,
        strict: bool = False
    ) -> pd.DataFrame:
        """
        Load data with column selection based on level.
        
        Parameters:
        -----------
        filepath : str
            Path to data file
        level : str
            Analysis level (psm, peptide, protein, msstats)
        source_format : str, optional
            Source format for column mapping (fragpipe, maxquant, diann)
        include_optional : bool
            Include optional columns if available
        strict : bool
            If True, raise error if required columns missing
        """
        
        # Get expected columns
        expected_cols = self.get_columns(level, include_optional)
        
        # Load full dataframe
        df = pd.read_csv(filepath, sep='\t' if filepath.endswith('.tsv') else ',')
        
        # Apply column mapping if source format specified
        if source_format and source_format in self.config['column_mappings']:
            mapping = self.config['column_mappings'][source_format]
            # Reverse mapping (source -> standard)
            reverse_map = {v: k for k, v in mapping.items()}
            df = df.rename(columns=reverse_map)
        
        # Check for required columns
        required_cols = self.config['levels'][level]['required']
        missing_required = set(required_cols) - set(df.columns)
        
        if missing_required:
            msg = f"Missing required columns for level '{level}': {missing_required}"
            if strict:
                raise ValueError(msg)
            else:
                warnings.warn(msg)
        
        # Select available columns from expected list
        available_cols = [col for col in expected_cols if col in df.columns]
        
        print(f"Loaded {len(df)} rows, {len(available_cols)}/{len(expected_cols)} columns for level '{level}'")
        if include_optional:
            missing_optional = set(self.config['levels'][level]['optional']) - set(df.columns)
            if missing_optional:
                print(f"Optional columns not found: {missing_optional}")
        
        return df[available_cols]


# Usage example
if __name__ == "__main__":
    loader = DataLoader("config.yaml")
    
    # Load protein-level data
    df_protein = loader.load_data(
        "combined_protein.tsv",
        level="protein",
        source_format="fragpipe",
        include_optional=True
    )
    
    # Load for MSstats
    df_msstats = loader.load_data(
        "psm.tsv",
        level="msstats",
        source_format="fragpipe",
        strict=True
    )
    
    # Check what columns are needed
    print("Columns for peptide level:")
    print(loader.get_columns("peptide"))