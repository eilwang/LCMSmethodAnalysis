"""
Test BPS loading with the provided sample data.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from diann_collection import DiannCollection

def test_bps_loading():
    """Test loading BPS format data."""
    bps_zip = "/Users/eileen.wang/Desktop/diann/SampleData/BPS/5bb65d07aa6a2f77f81b5e08ab034d2b.zip"

    print("=" * 80)
    print("Testing BPS Loading")
    print("=" * 80)
    print(f"\nLoading from: {bps_zip}")

    try:
        with DiannCollection() as collection:
            # Load from BPS zip
            collection.add_from_folder(
                bps_zip,
                levels=['precursor', 'protein', 'gene'],
                search_type='bps',
                strict=False
            )

            print("\n" + "=" * 80)
            print("Collection Summary")
            print("=" * 80)

            # Show what was loaded
            levels = collection.list_levels()
            print(f"\nLevels loaded: {levels}")

            for level in levels:
                adata = collection[level]
                samples = adata.var['UUID'].unique()

                # Check if search_type exists in var
                if 'search_type' in adata.var.columns:
                    search_types = adata.var['search_type'].unique()
                    search_types_str = f"Search types: {list(search_types)}"
                else:
                    search_types_str = "Search types: Not available (lost in concatenation)"

                print(f"\n{level.upper()} Level:")
                print(f"  Shape: {adata.shape}")
                print(f"  Samples: {list(samples)[:5]}{'...' if len(samples) > 5 else ''}")
                print(f"  {search_types_str}")
                print(f"  Obs columns: {adata.obs.columns.tolist()}")
                print(f"  Var columns: {adata.var.columns.tolist()}")
                print(f"  Layers: {list(adata.layers.keys())[:5]}{'...' if len(adata.layers.keys()) > 5 else ''}")

                # Show first few obs and var names
                print(f"  First 3 obs names: {adata.obs_names[:3].tolist()}")
                print(f"  First 3 var names: {adata.var_names[:3].tolist()}")

            print("\n" + "=" * 80)
            print("✓ BPS loading successful!")
            print("=" * 80)

    except Exception as e:
        print("\n" + "=" * 80)
        print("✗ Error during loading:")
        print("=" * 80)
        print(f"{type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_bps_loading()
