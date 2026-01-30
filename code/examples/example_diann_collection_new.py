"""
Example: Using DiannCollection (New Collection-Based Approach)

This script demonstrates how to use DiannCollection to manage multiple
DIA-NN search results as a collection object.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from diann_collection import DiannCollection


def example_basic_usage(zip_path: str):
    """Example 1: Basic collection usage."""
    print("=" * 80)
    print("EXAMPLE 1: BASIC USAGE")
    print("=" * 80)

    with DiannCollection() as collection:
        # Load data
        collection.add_from_zip(zip_path)

        # Basic info
        print(f"\nCollection: {collection}")
        print(f"Samples: {collection.list_samples()}")
        print(f"Number of samples: {len(collection)}")

        # Get levels per sample
        levels_dict = collection.list_levels()
        for sample, levels in levels_dict.items():
            print(f"  {sample}: {levels}")


def example_data_access(zip_path: str):
    """Example 2: Accessing data from collection."""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: DATA ACCESS")
    print("=" * 80)

    with DiannCollection() as collection:
        collection.add_from_zip(zip_path, levels=['precursor'])

        if len(collection) == 0:
            print("No samples loaded")
            return

        # Get first sample
        sample_name = collection.list_samples()[0]

        # Access specific AnnData
        adata = collection[sample_name, 'precursor']
        print(f"\n{sample_name} precursor data:")
        print(f"  Shape: {adata.shape}")
        print(f"  Observations: {adata.n_obs}")
        print(f"  Variables: {adata.n_vars}")
        print(f"  Layers: {list(adata.layers.keys())}")

        # Access all levels for a sample
        sample_data = collection[sample_name]
        print(f"\nAll levels for {sample_name}: {list(sample_data.keys())}")


def example_summary(zip_path: str):
    """Example 3: Generate summary."""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: SUMMARY GENERATION")
    print("=" * 80)

    with DiannCollection() as collection:
        collection.add_from_zip(zip_path, levels=['precursor'])

        # Generate summary
        summary = collection.summary_df()

        print("\nCollection Summary:")
        print(summary.to_string())


def example_persistence(zip_path: str):
    """Example 4: Save and load collection."""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: SAVING AND LOADING")
    print("=" * 80)

    # Create and save collection
    with DiannCollection() as collection:
        collection.add_from_zip(zip_path, levels=['precursor'])

        # Save to file
        save_path = "/tmp/diann_collection_example.pkl"
        collection.save(save_path)
        print(f"\nSaved collection to {save_path}")
        print(f"  Samples: {len(collection)}")

    # Load collection later
    loaded = DiannCollection.from_file(save_path)
    print(f"\nLoaded collection from {save_path}")
    print(f"  Samples: {len(loaded)}")
    print(f"  Sample names: {loaded.list_samples()}")


def example_anndata_operations(zip_path: str):
    """Example 5: Working with AnnData objects."""
    print("\n" + "=" * 80)
    print("EXAMPLE 5: ANNDATA OPERATIONS")
    print("=" * 80)

    with DiannCollection() as collection:
        collection.add_from_zip(zip_path, levels=['precursor'])

        if len(collection) == 0:
            print("No samples loaded")
            return

        sample_name = collection.list_samples()[0]
        adata = collection[sample_name, 'precursor']

        print(f"\nWorking with {sample_name} precursor data:")

        # Access components
        print(f"  Data matrix (X): {adata.X.shape}")
        print(f"  Observations (obs): {adata.obs.shape}")
        print(f"    Columns: {list(adata.obs.columns)[:5]}...")  # First 5 columns
        print(f"  Variables (var): {adata.var.shape}")
        print(f"    Columns: {list(adata.var.columns)[:5]}...")  # First 5 columns

        # Check layers
        if adata.layers:
            print(f"\n  Available layers:")
            for layer_name, layer_data in adata.layers.items():
                print(f"    {layer_name}: {layer_data.shape}")

        # Example: Get quantification values for first observation
        if adata.n_obs > 0:
            first_obs = adata.obs_names[0]
            values = adata[first_obs, :].X
            print(f"\n  First observation ({first_obs}):")
            print(f"    Quantification values shape: {values.shape}")
            print(f"    Sample: {adata.obs.loc[first_obs, 'Sample']}")


def example_iteration(zip_path: str):
    """Example 6: Iterating over collection."""
    print("\n" + "=" * 80)
    print("EXAMPLE 6: ITERATION")
    print("=" * 80)

    with DiannCollection() as collection:
        collection.add_from_zip(zip_path, levels=['precursor'])

        print("\nIterating over all samples and levels:")
        for sample_name in collection.list_samples():
            sample_levels = collection.list_levels(sample_name)
            print(f"\n{sample_name}:")

            for level in sample_levels:
                adata = collection[sample_name, level]
                print(f"  {level}: {adata.shape}")


# Main execution
if __name__ == "__main__":
    if len(sys.argv) > 1:
        zip_path = sys.argv[1]
    else:
        print("Usage: python example_diann_collection_new.py <path_to_zip>")
        print("\nExpected zip structure:")
        print("  diann_searches.zip/")
        print("    ├── sample1-tims-diann.result.zip")
        print("    │   └── results.tsv")
        print("    ├── sample2-tims-diann.result.zip")
        print("    │   └── results.tsv")
        print("    └── ...")
        sys.exit(1)

    # Run examples
    try:
        print("\n" + "=" * 80)
        print("DIA-NN COLLECTION EXAMPLES (NEW)")
        print("=" * 80)
        print(f"\nInput: {zip_path}\n")

        example_basic_usage(zip_path)
        example_data_access(zip_path)
        example_summary(zip_path)
        example_persistence(zip_path)
        example_anndata_operations(zip_path)
        example_iteration(zip_path)

        print("\n" + "=" * 80)
        print("✓ All examples completed successfully!")
        print("=" * 80)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
