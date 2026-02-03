"""
Comprehensive test of plotting features in MicroTOFMethodCollection
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ms_method_collection import MicroTOFMethodCollection
import matplotlib.pyplot as plt

# Load collection
collection = MicroTOFMethodCollection()
ms_folder = Path("/Users/eileen.wang/Desktop/diann/SampleData/methods/MS")
collection.add_methods_from_folder(str(ms_folder))

print(f"Loaded {len(collection)} methods")
print("=" * 80)

# Test 1: plot_windows with color_by_method=True (each method gets unique color)
print("\n1. Testing plot_windows (color by method)...")
try:
    ax = collection.plot_windows(
        method_names=['DIA003.proteoscape', 'DIA015.proteoscape'],
        color_by_method=True,
        alpha=0.5
    )
    if ax:
        plt.savefig('/tmp/test_windows_by_method.png', dpi=100)
        plt.close()
        print("   ✓ Success: Colored by method")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test 2: plot_windows with color_by_method=False (color by cycle)
print("\n2. Testing plot_windows (color by cycle)...")
try:
    ax = collection.plot_windows(
        method_names=['DIA003.proteoscape', 'DIA015.proteoscape'],
        color_by_method=False,
        alpha=0.5
    )
    if ax:
        plt.savefig('/tmp/test_windows_by_cycle.png', dpi=100)
        plt.close()
        print("   ✓ Success: Colored by cycle")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test 3: plot_differences with all methods
print("\n3. Testing plot_differences (auto-select top 20 numeric params)...")
try:
    fig = collection.plot_differences(
        method_names=['DIA003.proteoscape', 'DIA015.proteoscape']
    )
    if fig:
        plt.savefig('/tmp/test_differences_auto.png', dpi=100)
        plt.close()
        print("   ✓ Success: Auto-selected parameters")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test 4: plot_differences with specific parameters
print("\n4. Testing plot_differences (specific parameters)...")
try:
    specific_params = [
        'TOF_DetectorTofSetValue',
        'negative_default_Calibration_Tof2CalC0',
        'positive_default_Calibration_Tof2CalC0'
    ]
    fig = collection.plot_differences(
        method_names=['DIA003.proteoscape', 'DIA015.proteoscape'],
        param_names=specific_params
    )
    if fig:
        plt.savefig('/tmp/test_differences_specific.png', dpi=100)
        plt.close()
        print("   ✓ Success: Specific parameters")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test 5: Verify DataFrame integration
print("\n5. Testing DataFrame integration...")
try:
    result = collection.find_differences(
        method_names=['DIA003.proteoscape', 'DIA015.proteoscape']
    )
    print(f"   ✓ Found {len(result['param_differences_df'])} parameter differences")
    print(f"   ✓ Found {len(result['dia_differences_df'])} DIA differences")
except Exception as e:
    print(f"   ✗ Error: {e}")

print("\n" + "=" * 80)
print("FEATURE SUMMARY")
print("=" * 80)
print("\n✓ plot_windows() - Overlay DIA windows")
print("  Options:")
print("    - color_by_method: Each method gets unique color")
print("    - color_by_cycle: Windows colored by cycle ID")
print("    - alpha, edge_color, figsize, show_labels")
print("\n✓ plot_differences() - Visualize parameter differences")
print("  Options:")
print("    - Auto-select top 20 numeric parameters")
print("    - Specify param_names for custom selection")
print("    - Scatter plot with connecting lines shows value spread")
print("\n✓ Both methods integrate seamlessly with find_differences()")
print("=" * 80)
