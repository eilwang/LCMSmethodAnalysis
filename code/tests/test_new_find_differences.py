"""Test the new unified find_differences method."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from LCMSmethodAnalysis.parsers.timsmeth.ms_method_collection import MicroTOFMethodCollection

print("Testing New Unified find_differences()")
print("=" * 80)

# Load collection
collection = MicroTOFMethodCollection()
methods_folder = "/Users/eileen.wang/Desktop/diann/SampleData/methods/MS"
collection.add_methods_from_folder(methods_folder)

print(f"\nLoaded {len(collection)} methods")

# Get first two methods
method_names = collection.list_methods()[:2]
print(f"Comparing: {method_names}")
print("=" * 80)

# Call new find_differences - should return single DataFrame
diff_df = collection.find_differences(method_names)

print(f"\n1. Return type: {type(diff_df)}")
print(f"   Shape: {diff_df.shape}")
print(f"   Columns: {list(diff_df.columns)}")

# Show different types of differences
print(f"\n2. Breakdown by Type:")
if 'Type' in diff_df.columns:
    type_counts = diff_df['Type'].value_counts()
    for diff_type, count in type_counts.items():
        print(f"   {diff_type}: {count}")

# Show sample rows for each type
print(f"\n3. Sample differences by type:")

if 'Type' in diff_df.columns:
    for diff_type in diff_df['Type'].unique():
        print(f"\n   {diff_type}:")
        subset = diff_df[diff_df['Type'] == diff_type].head(3)
        for _, row in subset.iterrows():
            print(f"     {row['Parameter']}: {row['Description']}")
            for method in method_names:
                if method in row:
                    val = row[method]
                    # Truncate long values
                    val_str = str(val)[:60] + '...' if len(str(val)) > 60 else str(val)
                    print(f"       {method}: {val_str}")

# Check for DIA windows row
print(f"\n4. DIA windows comparison:")
if 'Type' in diff_df.columns:
    dia_windows_rows = diff_df[diff_df['Type'] == 'dia_windows']
    if len(dia_windows_rows) > 0:
        print(f"   Found {len(dia_windows_rows)} dia_windows row(s)")
        for _, row in dia_windows_rows.iterrows():
            print(f"   Parameter: {row['Parameter']}")
            print(f"   Description: {row['Description']}")
            for method in method_names:
                if method in row:
                    windows = row[method]
                    if windows is not None:
                        print(f"     {method}: DataFrame with shape {windows.shape}")
                    else:
                        print(f"     {method}: None")
    else:
        print("   No dia_windows rows (windows may be identical)")

# Show the actual DataFrame
print(f"\n5. Full DataFrame (first 10 rows):")
print(diff_df.head(10))

print(f"\n{'='*80}")
print("✓ New unified find_differences() test complete!")
print(f"{'='*80}")
