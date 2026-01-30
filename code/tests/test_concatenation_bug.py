"""Test to verify and diagnose the concatenation NaN bug."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from diann_collection import DiannCollection
import numpy as np

zip_path = "/Users/eileen.wang/Desktop/diann/SampleData/BPS/5bb65d07aa6a2f77f81b5e08ab034d2b.zip"

print("Testing concatenation bug...")
print("=" * 80)

with DiannCollection() as collection:
    # Load first sample
    print("\n1. Loading first sample...")
    collection.add_from_folder(
        zip_path,
        levels=['gene'],
        search_type='bps',
        strict=False
    )

    gene_data = collection['gene']
    print(f"\nAfter first load:")
    print(f"  Shape: {gene_data.shape}")
    print(f"  Samples: {sorted(gene_data.obs['Sample'].unique())[:3]}...")
    print(f"  Var (File.Name): {list(gene_data.var_names)[:3]}...")
    print(f"  X non-NaN: {(~np.isnan(gene_data.X)).sum()} / {gene_data.X.size}")
    print(f"  X non-zero: {(gene_data.X != 0).sum()} / {gene_data.X.size}")

    # Check first layer
    first_layer = list(gene_data.layers.keys())[0]
    layer_data = gene_data.layers[first_layer]
    print(f"  Layer '{first_layer}' non-NaN: {(~np.isnan(layer_data)).sum()} / {layer_data.size}")
    print(f"  Layer '{first_layer}' non-zero: {(layer_data != 0).sum()} / {layer_data.size}")

    # Now try to add same zip again (should concatenate)
    print("\n2. Loading same zip again (testing concatenation)...")
    collection.add_from_folder(
        zip_path,
        levels=['gene'],
        search_type='bps',
        strict=False
    )

    gene_data = collection['gene']
    print(f"\nAfter second load (concatenation):")
    print(f"  Shape: {gene_data.shape}")
    print(f"  Samples: {len(gene_data.obs['Sample'].unique())} unique")
    print(f"  Var (File.Name): {gene_data.var.shape}")
    print(f"  X non-NaN: {(~np.isnan(gene_data.X)).sum()} / {gene_data.X.size}")
    print(f"  X non-zero: {(gene_data.X != 0).sum()} / {gene_data.X.size}")
    print(f"  X all NaN: {np.isnan(gene_data.X).all()}")

    # Check first layer
    layer_data = gene_data.layers[first_layer]
    print(f"  Layer '{first_layer}' non-NaN: {(~np.isnan(layer_data)).sum()} / {layer_data.size}")
    print(f"  Layer '{first_layer}' non-zero: {(layer_data != 0).sum()} / {layer_data.size}")
    print(f"  Layer '{first_layer}' all NaN: {np.isnan(layer_data).all()}")

    # Check obs structure
    print(f"\n  Obs columns: {list(gene_data.obs.columns)}")
    print(f"  Obs index (first 3): {list(gene_data.obs.index)[:3]}")
    print(f"  Obs Sample (first 3): {list(gene_data.obs['Sample'])[:3]}")

    # Check var structure
    print(f"\n  Var columns: {list(gene_data.var.columns)}")
    print(f"  Var index (first 3): {list(gene_data.var.index)[:3]}")

print("\n" + "=" * 80)
print("✓ Test complete!")
print("=" * 80)
