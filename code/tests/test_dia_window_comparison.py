"""Test DIA window-by-window comparison."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from LCMSmethodAnalysis.parsers.timsmeth.ms_method_collection import MicroTOFMethodCollection

print("Testing DIA Window-by-Window Comparison")
print("=" * 80)

# Load collection
collection = MicroTOFMethodCollection()
methods_folder = "/Users/eileen.wang/Desktop/diann/SampleData/methods/MS"
collection.add_methods_from_folder(methods_folder)

print(f"\nLoaded {len(collection)} methods")

# Find methods with same window count
method_list = collection.list_methods()
window_counts = {}

for name in method_list:
    method = collection[name]
    if method.get('has_dia'):
        window_counts[name] = method.get('dia_window_count', 0)

print(f"\nWindow counts across methods:")
count_groups = {}
for name, count in window_counts.items():
    if count not in count_groups:
        count_groups[count] = []
    count_groups[count].append(name)

for count, names in sorted(count_groups.items()):
    print(f"  {count} windows: {len(names)} methods")
    if len(names) >= 2 and len(names) <= 5:
        print(f"    Examples: {names[:3]}")

# Pick two methods with same window count
for count, names in count_groups.items():
    if len(names) >= 2 and count > 0:
        test_methods = names[:2]
        print(f"\nTesting with methods having {count} windows:")
        print(f"  {test_methods}")

        # Compare them
        diff_df = collection.find_differences(test_methods)

        print(f"\n  Results:")
        print(f"    Total differences: {len(diff_df)}")

        if 'Type' in diff_df.columns:
            print(f"    By type:")
            for diff_type in diff_df['Type'].unique():
                count = len(diff_df[diff_df['Type'] == diff_type])
                print(f"      {diff_type}: {count}")

            # Check for dia_windows rows
            dia_windows_rows = diff_df[diff_df['Type'] == 'dia_windows']
            if len(dia_windows_rows) > 0:
                print(f"\n    ✓ Found dia_windows row with complete DataFrame objects!")
                for _, row in dia_windows_rows.iterrows():
                    for method in test_methods:
                        if method in row and row[method] is not None:
                            print(f"      {method}: {type(row[method])} shape {row[method].shape}")

            # Check for window_param differences
            window_param_rows = diff_df[diff_df['Type'] == 'dia_window_param']
            if len(window_param_rows) > 0:
                print(f"\n    ✓ Found {len(window_param_rows)} window parameter differences")
                print(f"      Examples:")
                for _, row in window_param_rows.head(5).iterrows():
                    print(f"        {row['Parameter']}: {row['Description']}")

        break  # Just test one pair

print(f"\n{'='*80}")
print("✓ DIA window comparison test complete!")
print(f"{'='*80}")
