"""Test comprehensive DIA comparison with various method pairs."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ms_method_collection import MicroTOFMethodCollection

print("Testing Comprehensive DIA Comparison")
print("=" * 80)

# Load collection
collection = MicroTOFMethodCollection()
methods_folder = "/Users/eileen.wang/Desktop/diann/SampleData/methods/MS"
collection.add_methods_from_folder(methods_folder)

# Test several pairs with same window count
test_pairs = [
    ['DIA007.proteoscape', 'DIA016.proteoscape'],  # 8 windows each
    ['DIA009.proteoscape', 'DIA018.proteoscape'],  # 12 windows each
    ['DIA008.proteoscape', 'DIA017.proteoscape'],  # 10 windows each
]

for pair in test_pairs:
    print(f"\n{'='*80}")
    print(f"Comparing: {pair}")

    # Get window info
    for name in pair:
        method = collection[name]
        if method.get('has_dia'):
            print(f"  {name}:")
            print(f"    Windows: {method.get('dia_window_count')}")
            print(f"    m/z: {method.get('dia_mz_min'):.1f} - {method.get('dia_mz_max'):.1f}")
            print(f"    IM: {method.get('dia_im_min'):.3f} - {method.get('dia_im_max'):.3f}")
            print(f"    Cycles: {method.get('dia_cycle_count')}")

    # Compare them
    diff_df = collection.find_differences(pair, include_params=False, include_polarity_configs=False)

    print(f"\n  DIA Differences found: {len(diff_df)}")

    if len(diff_df) > 0 and 'Type' in diff_df.columns:
        print(f"  By type:")
        for diff_type in diff_df['Type'].unique():
            count = len(diff_df[diff_df['Type'] == diff_type])
            print(f"    {diff_type}: {count}")

        # Show dia_stat differences
        dia_stat_rows = diff_df[diff_df['Type'] == 'dia_stat']
        if len(dia_stat_rows) > 0:
            print(f"\n  DIA Statistics differences:")
            for _, row in dia_stat_rows.iterrows():
                print(f"    {row['Parameter']}: {row['Description']}")
                for method in pair:
                    if method in row:
                        print(f"      {method}: {row[method]}")

        # Show window parameter differences
        window_param_rows = diff_df[diff_df['Type'] == 'dia_window_param']
        if len(window_param_rows) > 0:
            print(f"\n  Window parameter differences (first 5):")
            for _, row in window_param_rows.head(5).iterrows():
                print(f"    {row['Parameter']}: {row['Description']}")
                for method in pair:
                    if method in row:
                        print(f"      {method}: {row[method]}")

        # Check for dia_windows row
        dia_windows_rows = diff_df[diff_df['Type'] == 'dia_windows']
        if len(dia_windows_rows) > 0:
            print(f"\n  ✓ dia_windows row included with complete DataFrame objects:")
            for _, row in dia_windows_rows.iterrows():
                for method in pair:
                    if method in row and row[method] is not None:
                        windows = row[method]
                        print(f"    {method}: DataFrame shape {windows.shape}")
                        print(f"      Columns: {list(windows.columns)}")
    else:
        print("  No DIA differences (windows are identical)")

print(f"\n{'='*80}")
print("✓ Comprehensive DIA comparison complete!")
print(f"{'='*80}")
