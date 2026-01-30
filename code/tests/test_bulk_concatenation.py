"""Test bulk loading to verify no reindexing errors."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from diann_collection import DiannCollection
import numpy as np

zip_path = "/Users/eileen.wang/Desktop/diann/SampleData/BPS/5bb65d07aa6a2f77f81b5e08ab034d2b.zip"

print("Testing Bulk Loading (Multiple Samples)")
print("=" * 80)

try:
    with DiannCollection() as collection:
        print("\nLoading all samples from BPS zip...")
        collection.add_from_folder(
            zip_path,
            levels=['gene'],
            search_type='bps',
            strict=False
        )

        gene_data = collection['gene']

        print(f"\n✓ Successfully loaded!")
        print(f"  Shape: {gene_data.shape}")
        print(f"  Samples: {len(gene_data.var['UUID'].unique())} unique")
        print(f"  Obs index unique: {gene_data.obs.index.is_unique}")
        print(f"  Obs index duplicates: {gene_data.obs.index.duplicated().sum()}")

        # Check data integrity
        total_cells = gene_data.X.size
        non_nan = (~np.isnan(gene_data.X)).sum()
        nan_percent = 100 * (1 - non_nan / total_cells)

        print(f"\n✓ Data integrity:")
        print(f"  Total cells: {total_cells}")
        print(f"  Non-NaN: {non_nan} ({100 * non_nan / total_cells:.1f}%)")
        print(f"  NaN: {total_cells - non_nan} ({nan_percent:.1f}%)")

        # Try list_samples (tests var['UUID'] access)
        samples = collection.list_samples('gene')
        print(f"\n✓ list_samples works: {len(samples)} samples")

        # Try get with sample filter (tests var['UUID'] filtering)
        first_sample = samples[0]
        filtered = collection.get('gene', sample=first_sample)
        print(f"\n✓ Filtering by sample works:")
        print(f"  Single sample shape: {filtered.shape}")
        print(f"  Expected: ({gene_data.n_obs}, 1)")

        print(f"\n{'='*80}")
        print("✓✓✓ Bulk loading SUCCESSFUL - no reindexing errors! ✓✓✓")
        print(f"{'='*80}")

except Exception as e:
    print(f"\n{'='*80}")
    print(f"✗✗✗ ERROR: {type(e).__name__}")
    print(f"{'='*80}")
    print(f"{e}")
    import traceback
    traceback.print_exc()
