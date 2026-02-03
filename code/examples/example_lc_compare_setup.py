"""
Example: Comparing LC method setup parameters
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lc_method_collection import VNeoMethodCollection

# Create collection and load methods
collection = VNeoMethodCollection()
lc_folder = Path("/Users/eileen.wang/Desktop/diann/SampleData/methods/LC")

collection.add_method('20min', str(lc_folder / '20m150nlv15.meth'))
collection.add_method('25min', str(lc_folder / '25m150nlv5.meth'))
collection.add_method('36min', str(lc_folder / '36m150nlLong40.meth'))

print(f"Loaded {len(collection)} methods")
print("=" * 80)

# Compare all setup parameters
print("\n1. Compare all setup parameters:")
print("-" * 80)
setup_comparison = collection.compare_setup()
print(f"Shape: {setup_comparison.shape}")
print(f"Parameters: {len(setup_comparison)} parameters")
print(f"Methods: {len(setup_comparison.columns)} methods")
print()
print("First 15 parameters:")
print(setup_comparison.head(15))

# Find parameters that differ between methods
print("\n2. Find parameters with differences:")
print("-" * 80)
# Filter to rows where not all values are the same
different_params = setup_comparison[setup_comparison.nunique(axis=1) > 1]
print(f"Found {len(different_params)} parameters with differences")
print()
print("Parameters that differ:")
print(different_params)

# Show runtime comparison specifically
print("\n3. Runtime comparison:")
print("-" * 80)
runtime = setup_comparison.loc['Runtime [min]']
print(runtime)

# Save to CSV for further analysis
output_path = '/tmp/lc_method_setup_comparison.csv'
setup_comparison.to_csv(output_path)
print(f"\n✓ Saved full comparison to {output_path}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("\ncompare_setup() features:")
print("  - Compares ALL method parameters (runtime + params dict)")
print("  - Returns wide-format DataFrame (params as rows, methods as columns)")
print("  - Includes runtime, solvents, pump settings, column settings, etc.")
print("  - Easy to filter for differences or specific parameters")
print("=" * 80)
