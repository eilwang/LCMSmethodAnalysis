"""
Example: Using find_differences() with DataFrame output

The find_differences() method now returns DataFrames in wide format
for easier comparison and analysis of method differences.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ms_method_collection import MicroTOFMethodCollection

# Create collection and load methods
collection = MicroTOFMethodCollection()

ms_folder = Path("/Users/eileen.wang/Desktop/diann/SampleData/methods/MS")

# New simplified API - name is auto-extracted from path
collection.add_method(str(ms_folder / "DIA003.proteoscape.m"))  # Name: DIA003.proteoscape
collection.add_method(str(ms_folder / "DIA015.proteoscape.m.zip"))  # Name: DIA015.proteoscape.m

print("Loaded methods:", ', '.join(collection.list_methods()))

# Find all differences between methods
print("\n" + "=" * 80)
print("FINDING DIFFERENCES")
print("=" * 80)

result = collection.find_differences()

# The result contains DataFrames and summary
print("\nResult contains:")
for key in result.keys():
    print(f"  - {key}")

# Parameter differences as DataFrame (wide format)
print("\n" + "-" * 80)
print("PARAMETER DIFFERENCES (DataFrame)")
print("-" * 80)
print(f"Shape: {result['param_differences_df'].shape}")
print(f"\nFirst 5 parameters with differences:")
print(result['param_differences_df'].head())

# DIA differences as DataFrame (wide format)
print("\n" + "-" * 80)
print("DIA DIFFERENCES (DataFrame)")
print("-" * 80)
print(f"Shape: {result['dia_differences_df'].shape}")
print("\n", result['dia_differences_df'])

# You can save to CSV for further analysis
result['param_differences_df'].to_csv('/tmp/param_differences.csv')
result['dia_differences_df'].to_csv('/tmp/dia_differences.csv')
print("\n✓ Saved DataFrames to CSV files in /tmp/")

# Or work with the DataFrames directly
print("\n" + "-" * 80)
print("DATAFRAME ANALYSIS")
print("-" * 80)

# Example: Find parameters that differ significantly
param_df = result['param_differences_df']
print(f"\nTotal parameters with differences: {len(param_df)}")

# Example: Get parameters related to calibration
calib_params = param_df[param_df.index.str.contains('Calibration', na=False)]
print(f"Calibration-related differences: {len(calib_params)}")

# Print human-readable summary
print("\n" + "=" * 80)
print(result['summary'])
