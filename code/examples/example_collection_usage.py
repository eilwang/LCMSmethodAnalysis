"""
Comprehensive example of MicroTOFMethodCollection usage with simplified API.

All methods now support automatic name extraction from file paths.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ms_method_collection import MicroTOFMethodCollection

print("\n" + "=" * 80)
print("MS METHOD COLLECTION - SIMPLIFIED API EXAMPLES")
print("=" * 80)

ms_folder = Path("/Users/eileen.wang/Desktop/diann/SampleData/methods/MS")

# Example 1: Add single method with auto-extracted name
print("\n1. Add single method (name auto-extracted):")
print("-" * 80)
collection = MicroTOFMethodCollection()
collection.add_method(str(ms_folder / "DIA003.proteoscape.m"))
print(f"   Method added: {collection.list_methods()[0]}")
print(f"   Extracted from: DIA003.proteoscape.m → '{collection.list_methods()[0]}'")

# Example 2: Add single method with custom name
print("\n2. Add single method with custom name:")
print("-" * 80)
collection.add_method(str(ms_folder / "DIA015.proteoscape.m.zip"), name="MyCustomName")
print(f"   Methods: {', '.join(collection.list_methods())}")

# Example 3: Add multiple methods from list of paths
print("\n3. Add multiple methods from list (names auto-extracted):")
print("-" * 80)
collection2 = MicroTOFMethodCollection()
collection2.add_methods_from_paths([
    str(ms_folder / "DIA003.proteoscape.m"),
    str(ms_folder / "DIA015.proteoscape.m.zip")
])
print(f"   Loaded {len(collection2)} methods:")
for name in collection2.list_methods():
    print(f"     - {name}")

# Example 4: Add multiple methods with custom names (backward compatible)
print("\n4. Add multiple methods with custom names:")
print("-" * 80)
collection3 = MicroTOFMethodCollection()
collection3.add_methods_from_paths({
    'MethodA': str(ms_folder / "DIA003.proteoscape.m"),
    'MethodB': str(ms_folder / "DIA015.proteoscape.m.zip")
})
print(f"   Loaded {len(collection3)} methods:")
for name in collection3.list_methods():
    print(f"     - {name}")

# Example 5: Load all methods from folder (most convenient)
print("\n5. Load all methods from folder:")
print("-" * 80)
collection4 = MicroTOFMethodCollection()
collection4.add_methods_from_folder(str(ms_folder))
print(f"   Loaded {len(collection4)} methods from folder")
print(f"   First 5: {', '.join(collection4.list_methods()[:5])}")

# Example 6: Compare methods and get DataFrames
print("\n6. Compare methods (returns DataFrames):")
print("-" * 80)
result = collection2.find_differences()
print(f"   Identical: {result['identical']}")
print(f"   Parameter differences: {result['param_differences_df'].shape[0]} parameters differ")
print(f"   DIA differences: {result['dia_differences_df'].shape[0]} settings differ")

print("\n" + "=" * 80)
print("SUMMARY: API COMPARISON")
print("=" * 80)
print("\nOLD API (required explicit names):")
print("  collection.add_method('DIA003', '/path/to/DIA003.proteoscape.m')")
print("  collection.add_methods_from_paths({'name1': 'path1', 'name2': 'path2'})")
print("\nNEW API (names auto-extracted):")
print("  collection.add_method('/path/to/DIA003.proteoscape.m')  # Auto: 'DIA003.proteoscape'")
print("  collection.add_methods_from_paths(['/path/to/method1.m', '/path/to/method2.m'])")
print("  collection.add_methods_from_folder('/path/to/folder')  # Loads all .m and .zip files")
print("\nBoth APIs are supported for backward compatibility!")
print("=" * 80)
