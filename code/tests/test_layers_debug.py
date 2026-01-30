"""Debug empty layers issue."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from diann_collection import DiannCollection

zip_path = "/Users/eileen.wang/Desktop/diann/SampleData/BPS/5bb65d07aa6a2f77f81b5e08ab034d2b.zip"

print("Loading collection with one level...")

with DiannCollection() as collection:
    collection.add_from_zip(
        zip_path,
        levels=['precursor', 'gene'],  # Test both aggregated and non-aggregated
        search_type='bps',
        strict=False
    )

    # Check precursor (no aggregation)
    print("\n" + "=" * 80)
    print("PRECURSOR Level (no aggregation):")
    print("=" * 80)
    precursor_data = collection['precursor']
    print(f"  Shape: {precursor_data.shape}")
    print(f"  Layers: {list(precursor_data.layers.keys())[:5]}...")

    # Check first layer
    if len(precursor_data.layers) > 0:
        first_layer = list(precursor_data.layers.keys())[0]
        layer_data = precursor_data.layers[first_layer]
        print(f"\n  {first_layer}:")
        print(f"    Shape: {layer_data.shape}")
        print(f"    Non-null values: {(~pd.isna(layer_data)).sum()}")
        print(f"    Non-zero values: {(layer_data != 0).sum()}")
        print(f"    First row sample: {layer_data[0, :min(3, layer_data.shape[1])]}")

    # Check gene (with aggregation)
    print("\n" + "=" * 80)
    print("GENE Level (with aggregation):")
    print("=" * 80)
    gene_data = collection['gene']
    print(f"  Shape: {gene_data.shape}")
    print(f"  Layers: {list(gene_data.layers.keys())}")

    # Check if layers have data
    for layer_name in list(gene_data.layers.keys())[:3]:
        layer_data = gene_data.layers[layer_name]
        print(f"\n  {layer_name}:")
        print(f"    Shape: {layer_data.shape}")
        print(f"    Non-null values: {(~pd.isna(layer_data)).sum()}")
        print(f"    Non-zero values: {(layer_data != 0).sum()}")
        print(f"    First row sample: {layer_data[0, :min(3, layer_data.shape[1])]}")
