"""
Example: Visualizing method differences with plotting features

Demonstrates:
1. plot_windows - Overlay DIA windows from multiple methods
2. plot_differences - Scatter plot showing parameter value differences
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ms_method_collection import MSMethodCollection
import matplotlib.pyplot as plt

print("\n" + "=" * 80)
print("MS METHOD COLLECTION - PLOTTING EXAMPLES")
print("=" * 80)

# Load methods
collection = MSMethodCollection()
ms_folder = Path("/Users/eileen.wang/Desktop/diann/SampleData/methods/MS")

collection.add_method(str(ms_folder / "DIA003.proteoscape.m"))
collection.add_method(str(ms_folder / "DIA015.proteoscape.m.zip"))

print(f"\nLoaded {len(collection)} methods: {', '.join(collection.list_methods())}")

# Example 1: Plot DIA windows overlay
print("\n" + "-" * 80)
print("1. Plotting DIA Windows Overlay")
print("-" * 80)

ax = collection.plot_windows(
    method_names=['DIA003.proteoscape', 'DIA015.proteoscape.m'],
    color_by_method=True,
    alpha=0.5,
    figsize=(14, 8)
)

if ax:
    plt.savefig('/tmp/dia_windows_overlay.png', dpi=150, bbox_inches='tight')
    print("   ✓ Saved: /tmp/dia_windows_overlay.png")
    plt.close()

# Example 2: Plot parameter differences
print("\n" + "-" * 80)
print("2. Plotting Parameter Differences")
print("-" * 80)

fig = collection.plot_differences(
    method_names=['DIA003.proteoscape', 'DIA015.proteoscape.m'],
    figsize=(12, 10)
)

if fig:
    plt.savefig('/tmp/param_differences.png', dpi=150, bbox_inches='tight')
    print("   ✓ Saved: /tmp/param_differences.png")
    plt.close()

# Example 3: Plot specific parameters
print("\n" + "-" * 80)
print("3. Plotting Specific Parameters")
print("-" * 80)

specific_params = [
    'TOF_DetectorTofSetValue',
    'negative_default_Calibration_Tof2CalC0',
    'positive_default_Calibration_Tof2CalC0'
]

fig = collection.plot_differences(
    method_names=['DIA003.proteoscape', 'DIA015.proteoscape.m'],
    param_names=specific_params,
    figsize=(10, 6)
)

if fig:
    plt.savefig('/tmp/param_differences_specific.png', dpi=150, bbox_inches='tight')
    print("   ✓ Saved: /tmp/param_differences_specific.png")
    plt.close()

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("\nPlotting features added:")
print("  1. plot_windows() - Overlay DIA windows from multiple methods")
print("  2. plot_differences() - Visualize parameter differences with scatter plot")
print("\nUsage:")
print("  # Overlay DIA windows")
print("  collection.plot_windows(['method1', 'method2'], color_by_method=True)")
print()
print("  # Plot parameter differences")
print("  collection.plot_differences(['method1', 'method2'])")
print()
print("  # Plot specific parameters")
print("  collection.plot_differences(['method1', 'method2'], param_names=['param1', 'param2'])")
print("=" * 80)
