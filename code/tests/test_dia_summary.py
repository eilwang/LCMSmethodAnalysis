"""
Quick test to verify DIA window counting and summary parameters.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from LCMSmethodAnalysis.parsers.timsmeth.ms_method_collection import MicroTOFMethodCollection

# Create collection and load methods
collection = MicroTOFMethodCollection()
ms_folder = Path("/Users/eileen.wang/Desktop/diann/SampleData/methods/MS")

print("Adding methods...")
collection.add_method(str(ms_folder / "DIA003.proteoscape.m"), name="DIA003")
collection.add_method(str(ms_folder / "DIA015.proteoscape.m.zip"), name="DIA015")

print("\nMethods loaded:")
for name in collection.list_methods():
    method = collection[name]
    print(f"  - {name}")
    if method.dia:
        all_windows = len(method.dia.windows)
        ms1_windows = len(method.get_ms1_windows())
        dia_windows = len(method.get_dia_windows())
        all_cycles = method.get_cycle_ids()
        dia_cycles = method.get_dia_cycle_ids()
        print(f"    Total windows in DB: {all_windows}")
        print(f"    MS1 windows: {ms1_windows}")
        print(f"    DIA/PASEF windows: {dia_windows}")
        print(f"    All cycle IDs: {all_cycles} (count: {len(all_cycles)})")
        print(f"    DIA cycle IDs (excluding MS1): {dia_cycles} (count: {len(dia_cycles)})")

print("\n" + "=" * 80)
print("SUMMARY DATAFRAME")
print("=" * 80)
summary = collection.summary_df()
print(summary.to_string())

print("\n" + "=" * 80)
print("DIA PARAMETERS (detailed view)")
print("=" * 80)
dia_cols = [col for col in summary.columns if 'DIA' in col]
print(summary[['Method'] + dia_cols].to_string())

print("\n✓ Test completed successfully!")
