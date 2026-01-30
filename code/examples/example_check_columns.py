"""
Example: Efficient Column Checking

This example demonstrates the new check_available_levels() method that
checks which levels can be loaded from a file WITHOUT loading all the data first.

This is much more efficient than the previous approach that would load the
entire TSV file before discovering missing columns.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from anndiannloader import DiannLoader


def example_check_columns(results_path: str):
    """Example: Check which levels are available before loading."""
    print("=" * 80)
    print("EXAMPLE: EFFICIENT COLUMN CHECKING")
    print("=" * 80)

    loader = DiannLoader()

    # Check available levels (only reads header - very fast!)
    print(f"\nChecking available levels in: {results_path}")
    available = loader.check_available_levels(results_path)

    print("\nLevel availability:")
    for level, info in available.items():
        status = "✓ Available" if info['available'] else "✗ Missing columns"
        print(f"\n  {level}: {status}")
        print(f"    Required columns: {info['total_required']}")
        print(f"    Present: {len(info['present_columns'])}")

        if not info['available']:
            missing = info['missing_columns']
            print(f"    Missing: {', '.join(missing[:5])}{'...' if len(missing) > 5 else ''}")

    # Now you can load only the levels that are available
    print("\n" + "=" * 80)
    print("Loading only available levels:")
    print("=" * 80)

    for level, info in available.items():
        if info['available']:
            print(f"\nLoading {level} level...")
            adata = loader.load_to_adata(results_path, level=level, strict=False)
            print(f"  ✓ Loaded: {adata.shape}")
        else:
            print(f"\n⚠ Skipping {level} level (missing required columns)")


# Main execution
if __name__ == "__main__":
    if len(sys.argv) > 1:
        results_path = sys.argv[1]
    else:
        print("Usage: python example_check_columns.py <path_to_results.tsv>")
        sys.exit(1)

    example_check_columns(results_path)
