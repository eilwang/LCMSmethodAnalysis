"""
Test enhanced find_differences method with polarity config comparison.
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

print("\n" + "=" * 80)
print("TEST 1: Find all differences")
print("=" * 80)
diffs1 = collection.find_differences()
print(diffs1['summary'])
print("\nGlobal parameters with differences:", len(diffs1['param_differences_df']))
print("Polarity parameters with differences:", len(diffs1['polarity_differences_df']))
print("DIA parameters with differences:", len(diffs1['dia_differences_df']))

print("\n" + "=" * 80)
print("TEST 2: Find only polarity config differences")
print("=" * 80)
diffs2 = collection.find_differences(
    include_params=False,
    include_dia=False,
    include_polarity_configs=True
)
print(diffs2['summary'])
if not diffs2['polarity_differences_df'].empty:
    print("\nPolarity parameters that differ:")
    print(diffs2['polarity_differences_df'].to_string())

print("\n" + "=" * 80)
print("TEST 3: Find only positive polarity differences")
print("=" * 80)
diffs3 = collection.find_differences(
    include_params=False,
    include_dia=False,
    polarities=['positive']
)
print(f"Found {len(diffs3['polarity_differences_df'])} positive polarity differences")
if not diffs3['polarity_differences_df'].empty:
    print(diffs3['polarity_differences_df'].to_string())

print("\n" + "=" * 80)
print("TEST 4: Find only CaptiveSpray source differences")
print("=" * 80)
diffs4 = collection.find_differences(
    include_params=False,
    include_dia=False,
    sources=['captivespray']
)
print(f"Found {len(diffs4['polarity_differences_df'])} CaptiveSpray differences")
if not diffs4['polarity_differences_df'].empty:
    print(diffs4['polarity_differences_df'].to_string())

print("\n" + "=" * 80)
print("TEST 5: Find only DIA differences")
print("=" * 80)
diffs5 = collection.find_differences(
    include_params=False,
    include_polarity_configs=False,
    include_dia=True
)
print(f"Found {len(diffs5['dia_differences_df'])} DIA differences")
if not diffs5['dia_differences_df'].empty:
    print(diffs5['dia_differences_df'].head(20).to_string())

print("\n✓ All tests completed successfully!")
