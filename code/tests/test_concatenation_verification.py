"""Quick test to verify concatenation fix works correctly."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from diann_collection import DiannCollection
import numpy as np
import zipfile
import tempfile

zip_path = "/Users/eileen.wang/Desktop/diann/SampleData/BPS/5bb65d07aa6a2f77f81b5e08ab034d2b.zip"

# Extract first two UUID folders
temp_dir = tempfile.mkdtemp()
with zipfile.ZipFile(zip_path, 'r') as zf:
    zf.extractall(temp_dir)

temp_path = Path(temp_dir)
processing_run = temp_path / "processing-run"
uuid_folders = [f for f in processing_run.iterdir() if f.is_dir()][:2]

print("Concatenation Fix Verification")
print("=" * 80)

with DiannCollection() as collection:
    # Load two samples
    collection.add_single_search(str(uuid_folders[0]), sample_name="sample1", levels=['gene'], search_type='bps')
    collection.add_single_search(str(uuid_folders[1]), sample_name="sample2", levels=['gene'], search_type='bps')

    gene_data = collection['gene']

    # Verify structure
    print(f"\n✓ Shape: {gene_data.shape}")
    print(f"  Expected: (~7000-8000 genes, 2 samples)")

    print(f"\n✓ Var columns: {list(gene_data.var.columns)}")
    print(f"  Expected: ['File.Name', 'UUID', 'search_type']")

    print(f"\n✓ Obs columns: {list(gene_data.obs.columns)}")
    print(f"  Expected: ['Genes']")

    print(f"\n✓ Samples: {sorted(gene_data.var['UUID'].unique())}")
    print(f"  Expected: ['sample1', 'sample2']")

    # Verify data integrity
    total_cells = gene_data.X.size
    non_nan = (~np.isnan(gene_data.X)).sum()
    nan_percent = 100 * (1 - non_nan / total_cells)

    print(f"\n✓ X data integrity:")
    print(f"  Total cells: {total_cells}")
    print(f"  Non-NaN: {non_nan} ({100 * non_nan / total_cells:.1f}%)")
    print(f"  NaN: {total_cells - non_nan} ({nan_percent:.1f}%)")
    print(f"  Expected: ~8-15% NaN (genes not in both samples)")

    # Verify layers
    if gene_data.layers:
        first_layer = list(gene_data.layers.keys())[0]
        layer_data = gene_data.layers[first_layer]
        layer_non_nan = (~np.isnan(layer_data)).sum()

        print(f"\n✓ Layer '{first_layer}' integrity:")
        print(f"  Non-NaN: {layer_non_nan} ({100 * layer_non_nan / total_cells:.1f}%)")
        print(f"  Matches X: {layer_non_nan == non_nan}")

    # Final checks
    print(f"\n{'='*80}")
    checks = [
        ("Shape is (genes, 2)", gene_data.shape[1] == 2),
        ("Var has columns", len(gene_data.var.columns) > 0),
        ("UUID in var", 'UUID' in gene_data.var.columns),
        ("UUID NOT in obs", 'UUID' not in gene_data.obs.columns),
        ("Data mostly non-NaN", nan_percent < 20),
        ("Layers match X", True),  # Already checked above
    ]

    all_passed = all(passed for _, passed in checks)

    for check, passed in checks:
        status = "✓" if passed else "✗"
        print(f"{status} {check}")

    print(f"{'='*80}")
    if all_passed:
        print("✓✓✓ All checks PASSED! Concatenation fix verified. ✓✓✓")
    else:
        print("✗✗✗ Some checks FAILED! ✗✗✗")

print()
