"""
Example: Using markers to visualize gradient data points
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from LCMSmethodAnalysis.parsers.vneometh.lc_method_collection import VNeoMethodCollection
import matplotlib.pyplot as plt

# Create collection and load methods
collection = VNeoMethodCollection()
lc_folder = Path("/Users/eileen.wang/Desktop/diann/SampleData/methods/LC")

collection.add_method('20min', str(lc_folder / '20m150nlv15.meth'))
collection.add_method('25min', str(lc_folder / '25m150nlv5.meth'))
collection.add_method('36min', str(lc_folder / '36m150nlLong40.meth'))

print(f"Loaded {len(collection)} methods")
print("=" * 80)

# Create a 1x2 subplot layout to compare with and without markers
fig, axes = plt.subplots(1, 2, figsize=(16, 6))

# Test 1: Plot without markers (default)
print("\n1. Plotting without markers (default):")
collection.plot_gradients(
    method_names=['20min', '25min'],
    y_cols='Neo.PumpModule.Pump.%B.Value [%]',
    markers=False,
    ax=axes[0]
)
axes[0].set_title('Without Markers')
print("✓ Success")

# Test 2: Plot with markers
print("\n2. Plotting with markers:")
collection.plot_gradients(
    method_names=['20min', '25min'],
    y_cols='Neo.PumpModule.Pump.%B.Value [%]',
    markers=True,
    ax=axes[1]
)
axes[1].set_title('With Markers (shows gradient steps)')
print("✓ Success")

plt.tight_layout()
plt.savefig('/tmp/lc_gradient_markers.png', dpi=100)
print("\n✓ Saved plot to /tmp/lc_gradient_markers.png")

# Test 3: Plot with markers and twin axes
print("\n3. Plotting with markers and twin y-axes:")
axes_tuple = collection.plot_gradients(
    method_names=['20min', '25min'],
    y_cols=['Neo.PumpModule.Pump.%B.Value [%]',
            'Neo.PumpModule.Pump.Flow.Nominal [µl/min]'],
    twin_axes=True,
    markers=True,
    figsize=(12, 6)
)
plt.savefig('/tmp/lc_gradient_markers_twin.png', dpi=100)
plt.close()
print(f"✓ Success - Created plot with markers and twin axes")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("\nMarkers Feature:")
print("  - markers=False: Lines only (default)")
print("  - markers=True: Small circular markers with white outlines at data points")
print("\nBenefits:")
print("  - Visualize gradient step points clearly")
print("  - See exactly where gradient changes occur")
print("  - White outline makes markers visible against any color line")
print("\nMarker specifications:")
print("  - Shape: Circle (o)")
print("  - Size: 4pt")
print("  - Edge color: White")
print("  - Edge width: 0.8pt")
print("=" * 80)
