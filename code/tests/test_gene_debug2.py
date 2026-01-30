"""Debug gene level column selection."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import zipfile
import tempfile
import yaml

# Load one sample
zip_path = "/Users/eileen.wang/Desktop/diann/SampleData/BPS/5bb65d07aa6a2f77f81b5e08ab034d2b.zip"

# Extract
temp_dir = tempfile.mkdtemp()
with zipfile.ZipFile(zip_path, 'r') as zf:
    zf.extractall(temp_dir)

# Find first results file
temp_path = Path(temp_dir)
first_zip = list(temp_path.rglob("*tims-diann.result.zip"))[0]

nested_temp = tempfile.mkdtemp()
with zipfile.ZipFile(first_zip, 'r') as zf:
    zf.extractall(nested_temp)

results_tsv = list(Path(nested_temp).rglob("results.tsv"))[0]

# Load config
with open("diann_columns.yaml") as f:
    config = yaml.safe_load(f)

gene_config = config['levels']['gene']
print("Gene config:")
print(f"  obs: {gene_config['obs']}")
print(f"  var: {gene_config['var']}")
print(f"  layers: {gene_config['layers']}")

# Load data
df = pd.read_csv(results_tsv, sep='\t')
print(f"\nDataFrame shape: {df.shape}")
print(f"Columns: {list(df.columns)[:10]}...")

obs_name = 'Genes'
var_name = 'File.Name'
x_col = 'Genes.MaxLFQ'

print(f"\nChecking duplicates:")
print(f"  {obs_name} unique: {df[obs_name].nunique()} / {len(df)}")
print(f"  {var_name} unique: {df[var_name].nunique()} / {len(df)}")

# Check what available_obs_cols would be
obs_cols = gene_config.get('obs', [obs_name])
available_obs_cols = [col for col in obs_cols if col in df.columns]
print(f"\navailable_obs_cols: {available_obs_cols}")

# Try groupby
print(f"\nTrying groupby on {available_obs_cols + [var_name]}...")
grouped = df.groupby(available_obs_cols + [var_name], as_index=False).agg({x_col: 'max'})
print(f"Grouped shape: {grouped.shape}")
print(f"Grouped columns: {list(grouped.columns)}")
print(f"\nGrouped {obs_name} unique: {grouped[obs_name].nunique()}")
print(f"Grouped {var_name} unique: {grouped[var_name].nunique()}")

# Check for duplicates in grouped
print(f"\nChecking duplicates in grouped data:")
dups_obs = grouped[obs_name].duplicated().sum()
dups_var = grouped[var_name].duplicated().sum()
dups_both = grouped.duplicated(subset=available_obs_cols + [var_name]).sum()
print(f"  Duplicate {obs_name}: {dups_obs}")
print(f"  Duplicate {var_name}: {dups_var}")
print(f"  Duplicate ({obs_name}, {var_name}): {dups_both}")

# Try pivot
try:
    print(f"\nTrying pivot with index={available_obs_cols}, columns={var_name}, values={x_col}...")
    pivot_df = grouped.pivot(index=available_obs_cols, columns=var_name, values=x_col)
    print(f"✓ Pivot success! Shape: {pivot_df.shape}")
except Exception as e:
    print(f"✗ Pivot failed: {e}")
    # Show first few rows of grouped to diagnose
    print("\nFirst 10 rows of grouped:")
    print(grouped.head(10))
