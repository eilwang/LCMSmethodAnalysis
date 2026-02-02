"""Test the to_dataframe method for MSMethodCollection."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ms_method_collection import MSMethodCollection

print("Testing to_dataframe() Method")
print("=" * 80)

# Load collection
collection = MSMethodCollection()
methods_folder = "/Users/eileen.wang/Desktop/diann/SampleData/methods/MS"
collection.add_methods_from_folder(methods_folder)

print(f"\nLoaded {len(collection)} methods")

# Test 1: Get all methods and parameters
print(f"\n{'='*80}")
print("Test 1: Full DataFrame (all methods, all parameters except dia_windows)")
print("=" * 80)

df_full = collection.to_dataframe()
print(f"Shape: {df_full.shape}")
print(f"  {df_full.shape[1]} parameters (rows)")
print(f"  {df_full.shape[0]} methods (columns)")
print(f"\nFirst 5 parameters:")
print(df_full.iloc[:, :5].head())

# Test 2: Specific methods
print(f"\n{'='*80}")
print("Test 2: Subset by Methods")
print("=" * 80)

df_subset = collection.to_dataframe(
    method_names=['DIA007.proteoscape', 'DIA016.proteoscape', 'DIA018.proteoscape']
)
print(f"Shape: {df_subset.shape}")
print(f"Methods: {list(df_subset.index)}")
print(f"\nFirst 10 parameters:")
print(df_subset.iloc[:, :10])

# Test 3: Specific parameters
print(f"\n{'='*80}")
print("Test 3: Subset by Parameters")
print("=" * 80)

params_of_interest = [
    'Collision_GasSupply_Set',
    'TOF_DetectorTofSetValue',
    'dia_window_count',
    'dia_mz_min',
    'dia_mz_max',
    'dia_cycle_count'
]

df_params = collection.to_dataframe(param_names=params_of_interest)
print(f"Shape: {df_params.shape}")
print(f"\nAll methods (first 5), selected parameters:")
print(df_params.iloc[:5])

# Test 4: Specific methods AND parameters
print(f"\n{'='*80}")
print("Test 4: Subset by Both Methods and Parameters")
print("=" * 80)

df_both = collection.to_dataframe(
    method_names=['DIA007.proteoscape', 'DIA016.proteoscape'],
    param_names=params_of_interest
)
print(f"Shape: {df_both.shape}")
print(df_both)

# Test 5: Filter after creation
print(f"\n{'='*80}")
print("Test 5: Filter DataFrame After Creation")
print("=" * 80)

df_full = collection.to_dataframe()

# Filter to parameters starting with 'dia_'
dia_params = [col for col in df_full.columns if col.startswith('dia_')]
df_dia = df_full[dia_params]
print(f"DIA parameters shape: {df_dia.shape}")
print(f"DIA parameters: {dia_params[:10]}...")  # First 10

# Filter to specific methods (rows)
methods_subset = ['DIA007.proteoscape', 'DIA016.proteoscape', 'DIA018.proteoscape']
df_methods = df_full.loc[methods_subset]
print(f"\nSubset of 3 methods shape: {df_methods.shape}")
print(f"\nFirst 5 params for these methods:")
print(df_methods.iloc[:, :5])

# Test 6: Include dia_windows (for demonstration)
print(f"\n{'='*80}")
print("Test 6: Include dia_windows (DataFrame objects)")
print("=" * 80)

df_with_windows = collection.to_dataframe(
    method_names=['DIA007.proteoscape', 'DIA016.proteoscape'],
    param_names=['dia_window_count', 'dia_windows'],
    exclude_dia_windows=False
)
print(f"Shape: {df_with_windows.shape}")
print(f"\nNote: dia_windows contains DataFrame objects:")
print(df_with_windows)

# Check the type of dia_windows value
windows_val = df_with_windows.loc['DIA007.proteoscape', 'dia_windows']
print(f"\nType of dia_windows value: {type(windows_val)}")
if hasattr(windows_val, 'shape'):
    print(f"Shape of DIA windows DataFrame: {windows_val.shape}")

# Test 7: Finding differences using DataFrame
print(f"\n{'='*80}")
print("Test 7: Using DataFrame to Find Differences")
print("=" * 80)

df_compare = collection.to_dataframe(
    method_names=['DIA007.proteoscape', 'DIA016.proteoscape']
)

# Find parameters that differ between these two methods
differences = []
for param in df_compare.columns:
    val1 = df_compare.loc['DIA007.proteoscape', param]
    val2 = df_compare.loc['DIA016.proteoscape', param]

    # Compare (accounting for NaN)
    try:
        if val1 != val2:
            # Check if both are NaN
            import pandas as pd
            if not (pd.isna(val1) and pd.isna(val2)):
                differences.append(param)
    except:
        # For unhashable types like lists
        if str(val1) != str(val2):
            differences.append(param)

print(f"Found {len(differences)} parameters that differ")
print(f"First 10 differences: {differences[:10]}")

print(f"\n{'='*80}")
print("✓ to_dataframe() tests complete!")
print(f"{'='*80}")
