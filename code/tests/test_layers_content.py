"""Test that layers contain data after loading."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from anndiannloader import DiannLoader
import zipfile
import tempfile

# Load one sample and check layers
zip_path = "/Users/eileen.wang/Desktop/diann/SampleData/BPS/5bb65d07aa6a2f77f81b5e08ab034d2b.zip"

# Extract and find first results file
temp_dir = tempfile.mkdtemp()
with zipfile.ZipFile(zip_path, 'r') as zf:
    zf.extractall(temp_dir)

temp_path = Path(temp_dir)
first_zip = list(temp_path.rglob("*tims-diann.result.zip"))[0]

nested_temp = tempfile.mkdtemp()
with zipfile.ZipFile(first_zip, 'r') as zf:
    zf.extractall(nested_temp)

results_tsv = list(Path(nested_temp).rglob("results.tsv"))[0]

print(f"Testing layers for: {results_tsv.parent.name}")
print("=" * 80)

loader = DiannLoader()

# Test gene level (with aggregation)
print("\nGENE LEVEL (aggregated):")
print("-" * 80)
adata_gene = loader.load_to_adata(str(results_tsv), level='gene', strict=False)
print(f"Shape: {adata_gene.shape}")
print(f"Number of layers: {len(adata_gene.layers)}")
print(f"Layer names: {list(adata_gene.layers.keys())}")

# Check first 3 layers
for layer_name in list(adata_gene.layers.keys())[:3]:
    layer_data = adata_gene.layers[layer_name]
    non_null = (~np.isnan(layer_data)).sum()
    non_zero = (layer_data != 0).sum()
    print(f"\n  {layer_name}:")
    print(f"    Non-null: {non_null}/{layer_data.size} ({100*non_null/layer_data.size:.1f}%)")
    print(f"    Non-zero: {non_zero}/{layer_data.size} ({100*non_zero/layer_data.size:.1f}%)")
    if non_null > 0:
        print(f"    Sample values: {layer_data.flatten()[~np.isnan(layer_data.flatten())][:3]}")

# Test precursor level (no aggregation)
print("\n" + "=" * 80)
print("PRECURSOR LEVEL (no aggregation):")
print("-" * 80)
adata_precursor = loader.load_to_adata(str(results_tsv), level='precursor', strict=False)
print(f"Shape: {adata_precursor.shape}")
print(f"Number of layers: {len(adata_precursor.layers)}")
print(f"Layer names: {list(adata_precursor.layers.keys())[:5]}...")

# Check first 3 layers
for layer_name in list(adata_precursor.layers.keys())[:3]:
    layer_data = adata_precursor.layers[layer_name]
    non_null = (~np.isnan(layer_data)).sum()
    non_zero = (layer_data != 0).sum()
    print(f"\n  {layer_name}:")
    print(f"    Non-null: {non_null}/{layer_data.size} ({100*non_null/layer_data.size:.1f}%)")
    print(f"    Non-zero: {non_zero}/{layer_data.size} ({100*non_zero/layer_data.size:.1f}%)")
    if non_null > 0:
        print(f"    Sample values: {layer_data.flatten()[~np.isnan(layer_data.flatten())][:3]}")

print("\n" + "=" * 80)
print("✓ Layer content test complete!")
print("=" * 80)
