"""Test adding single samples one at a time to see NaN bug."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from diann_collection import DiannCollection
import numpy as np
import zipfile
import tempfile

zip_path = "/Users/eileen.wang/Desktop/diann/SampleData/BPS/5bb65d07aa6a2f77f81b5e08ab034d2b.zip"

# Extract and find first two UUID folders
temp_dir = tempfile.mkdtemp()
with zipfile.ZipFile(zip_path, 'r') as zf:
    zf.extractall(temp_dir)

temp_path = Path(temp_dir)
processing_run = temp_path / "processing-run"
uuid_folders = [f for f in processing_run.iterdir() if f.is_dir()][:2]

print("Testing single sample addition bug...")
print("=" * 80)
print(f"Found test folders: {[f.name for f in uuid_folders]}")

with DiannCollection() as collection:
    # Load first search
    print("\n1. Loading first search...")
    collection.add_single_search(
        str(uuid_folders[0]),
        sample_name="search_1",
        levels=['gene'],
        search_type='bps'
    )

    gene_data = collection['gene']
    print(f"\nAfter first search:")
    print(f"  Shape: {gene_data.shape}")
    print(f"  Var shape: {gene_data.var.shape}")
    print(f"  Var columns: {list(gene_data.var.columns)}")
    print(f"  X non-NaN: {(~np.isnan(gene_data.X)).sum()} / {gene_data.X.size}")
    print(f"  X sample values: {gene_data.X.flatten()[~np.isnan(gene_data.X.flatten())][:5]}")

    # Check first layer
    first_layer = list(gene_data.layers.keys())[0]
    layer_data = gene_data.layers[first_layer]
    print(f"  Layer '{first_layer}' non-NaN: {(~np.isnan(layer_data)).sum()} / {layer_data.size}")
    print(f"  Layer '{first_layer}' sample values: {layer_data.flatten()[~np.isnan(layer_data.flatten())][:5]}")

    # Load second search
    print("\n2. Loading second search (should concatenate)...")
    collection.add_single_search(
        str(uuid_folders[1]),
        sample_name="search_2",
        levels=['gene'],
        search_type='bps'
    )

    gene_data = collection['gene']
    print(f"\nAfter second search:")
    print(f"  Shape: {gene_data.shape}")
    print(f"  Var shape: {gene_data.var.shape}")
    print(f"  Var columns: {list(gene_data.var.columns)}")
    print(f"  X non-NaN: {(~np.isnan(gene_data.X)).sum()} / {gene_data.X.size}")
    print(f"  X all NaN? {np.isnan(gene_data.X).all()}")

    if (~np.isnan(gene_data.X)).sum() > 0:
        print(f"  X sample non-NaN values: {gene_data.X.flatten()[~np.isnan(gene_data.X.flatten())][:5]}")
    else:
        print(f"  X is ALL NaN!")

    # Check first layer
    layer_data = gene_data.layers[first_layer]
    print(f"  Layer '{first_layer}' non-NaN: {(~np.isnan(layer_data)).sum()} / {layer_data.size}")
    print(f"  Layer '{first_layer}' all NaN? {np.isnan(layer_data).all()}")

    if (~np.isnan(layer_data)).sum() > 0:
        print(f"  Layer '{first_layer}' sample non-NaN values: {layer_data.flatten()[~np.isnan(layer_data.flatten())][:5]}")
    else:
        print(f"  Layer '{first_layer}' is ALL NaN!")

    # Debug: check the actual structure
    print(f"\n  Obs shape: {gene_data.obs.shape}")
    print(f"  Obs columns: {list(gene_data.obs.columns)}")
    print(f"  Obs index (first 5): {list(gene_data.obs.index)[:5]}")
    print(f"  Var Sample values (all): {list(gene_data.var['UUID'])}")

    print(f"\n  Var shape: {gene_data.var.shape}")
    print(f"  Var index (first 5): {list(gene_data.var.index)[:min(5, len(gene_data.var.index))]}")

print("\n" + "=" * 80)
print("✓ Test complete!")
print("=" * 80)
