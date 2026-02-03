"""
Example: Loading and Merging Multiple DIA-NN Search Results

This script demonstrates how to use DiannCollectionLoader to:
1. Load multiple DIA-NN search results from a zip archive
2. Merge results at different analysis levels (precursor, protein, gene)
3. Create AnnData objects for downstream analysis
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from code.archive.diann_collection_loader import DiannCollectionLoader
import pandas as pd


def example_basic_loading(zip_path: str):
    """Example 1: Basic loading and concatenation using load_from_folder."""
    print("=" * 80)
    print("EXAMPLE 1: BASIC LOADING (CONCAT METHOD) - load_from_folder")
    print("=" * 80)

    with DiannCollectionLoader() as loader:
        # Load precursor-level data and concatenate all samples
        # load_from_folder accepts both folders and zip files
        df = loader.load_from_folder(
            zip_path,
            level="precursor",
            merge_method='concat'  # Long format with all samples
        )

        print(f"\nLoaded {len(df)} total rows")
        print(f"Samples: {df['Sample'].unique()}")
        print(f"\nSample distribution:")
        print(df['Sample'].value_counts())

        return df


def example_protein_level(zip_path: str):
    """Example 2: Load at protein level with aggregation."""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: PROTEIN LEVEL LOADING")
    print("=" * 80)

    with DiannCollectionLoader() as loader:
        # Load protein-level data (automatically aggregates peptides)
        df_protein = loader.load_from_zip(
            zip_path,
            level="protein",
            merge_method='concat'
        )

        print(f"\nLoaded {len(df_protein)} protein groups")
        print(f"Samples: {df_protein['Sample'].unique()}")

        # Check aggregated columns
        agg_cols = [col for col in df_protein.columns if col.startswith('Num_') or col.startswith('Nunique_')]
        if agg_cols:
            print(f"\nAggregated statistics columns:")
            for col in agg_cols:
                print(f"  - {col}")

        return df_protein


def example_outer_merge(zip_path: str):
    """Example 3: Outer merge to create wide-format table."""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: OUTER MERGE (WIDE FORMAT)")
    print("=" * 80)

    with DiannCollectionLoader() as loader:
        # Outer merge keeps all features from all samples
        df_merged = loader.load_from_zip(
            zip_path,
            level="precursor",
            merge_method='outer'  # Wide format with merged features
        )

        print(f"\nMerged DataFrame shape: {df_merged.shape}")
        print(f"Total unique precursors: {df_merged.shape[0]}")

        return df_merged


def example_anndata_creation(zip_path: str):
    """Example 4: Create AnnData object for single-cell style analysis."""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: CREATING ANNDATA OBJECT")
    print("=" * 80)

    with DiannCollectionLoader() as loader:
        # Create merged AnnData object
        adata = loader.load_to_adata_collection(
            zip_path,
            level="precursor",
            merge_obs=True  # Merge all samples into one AnnData
        )

        print(f"\nAnnData created:")
        print(f"  Shape: {adata.shape}")
        print(f"  Observations (runs): {adata.n_obs}")
        print(f"  Variables (precursors): {adata.n_vars}")
        print(f"\nLayers available:")
        for layer in adata.layers.keys():
            print(f"  - {layer}")

        print(f"\nObservation metadata columns:")
        for col in adata.obs.columns:
            print(f"  - {col}")

        print(f"\nVariable metadata columns:")
        for col in adata.var.columns[:10]:  # Show first 10
            print(f"  - {col}")

        return adata


def example_specific_sections(zip_path: str):
    """Example 5: Load only specific sections."""
    print("\n" + "=" * 80)
    print("EXAMPLE 5: LOADING SPECIFIC SECTIONS")
    print("=" * 80)

    with DiannCollectionLoader() as loader:
        # Load only essential columns
        df_minimal = loader.load_from_zip(
            zip_path,
            level="precursor",
            sections=["var", "obs", "x"],  # Only var names, obs names, and quantification
            merge_method='concat'
        )

        print(f"\nMinimal DataFrame shape: {df_minimal.shape}")
        print(f"Columns loaded: {list(df_minimal.columns)}")

        return df_minimal


def example_multi_level_analysis(zip_path: str):
    """Example 6: Load and analyze at multiple levels."""
    print("\n" + "=" * 80)
    print("EXAMPLE 6: MULTI-LEVEL ANALYSIS")
    print("=" * 80)

    results = {}

    with DiannCollectionLoader() as loader:
        # Load at each level
        for level in ["precursor", "protein"]:
            print(f"\nLoading {level} level...")
            df = loader.load_from_zip(
                zip_path,
                level=level,
                merge_method='concat'
            )
            results[level] = df

            print(f"  {level.capitalize()}: {len(df)} rows")

    # Compare levels
    print("\n" + "-" * 80)
    print("LEVEL COMPARISON")
    print("-" * 80)

    for level, df in results.items():
        samples = df['Sample'].unique()
        print(f"\n{level.capitalize()} level:")
        print(f"  Total rows: {len(df)}")
        print(f"  Samples: {len(samples)}")
        print(f"  Avg rows per sample: {len(df) / len(samples):.0f}")

    return results


def example_load_all_levels(zip_path: str):
    """Example 7: Load all levels at once."""
    print("\n" + "=" * 80)
    print("EXAMPLE 7: LOAD ALL LEVELS AT ONCE")
    print("=" * 80)

    with DiannCollectionLoader() as loader:
        # Load all levels in one call
        all_levels = loader.load_from_folder(
            zip_path,
            level=None,  # or level='all'
            merge_method='concat'
        )

        print("\n" + "-" * 80)
        print("ALL LEVELS LOADED")
        print("-" * 80)

        # Show what was loaded
        print(f"\nLoaded {len(all_levels)} levels: {list(all_levels.keys())}")

        # Compare all levels
        for level, df in all_levels.items():
            samples = df['Sample'].unique()
            print(f"\n{level.capitalize()} level:")
            print(f"  Shape: {df.shape}")
            print(f"  Samples: {len(samples)}")
            print(f"  Avg rows per sample: {len(df) / len(samples):.0f}")

        return all_levels


# Main execution
if __name__ == "__main__":
    if len(sys.argv) > 1:
        zip_path = sys.argv[1]
    else:
        print("Usage: python example_diann_collection.py <path_to_zip>")
        print("\nExpected zip structure:")
        print("  diann_searches.zip/")
        print("    ├── sample1-tims-diann.result.zip")
        print("    │   └── results.tsv")
        print("    ├── sample2-tims-diann.result.zip")
        print("    │   └── results.tsv")
        print("    └── ...")
        print("\nOr flattened structure:")
        print("  diann_searches.zip/")
        print("    ├── sample1/")
        print("    │   └── results.tsv")
        print("    ├── sample2/")
        print("    │   └── results.tsv")
        print("    └── ...")
        sys.exit(1)

    # Run examples
    try:
        print("\n" + "=" * 80)
        print("DIA-NN COLLECTION LOADER EXAMPLES")
        print("=" * 80)
        print(f"\nInput: {zip_path}\n")

        # Example 1: Basic loading
        df_concat = example_basic_loading(zip_path)

        # Example 2: Protein level
        df_protein = example_protein_level(zip_path)

        # Example 3: Outer merge
        df_merged = example_outer_merge(zip_path)

        # Example 4: AnnData
        adata = example_anndata_creation(zip_path)

        # Example 5: Specific sections
        df_minimal = example_specific_sections(zip_path)

        # Example 6: Multi-level
        results_multi = example_multi_level_analysis(zip_path)

        # Example 7: Load all levels at once
        all_levels = example_load_all_levels(zip_path)

        print("\n" + "=" * 80)
        print("✓ All examples completed successfully!")
        print("=" * 80)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
