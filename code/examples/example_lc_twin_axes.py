"""
Example: Using twin y-axes for plotting gradients with different scales
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lc_method_collection import LCMethodCollection
import matplotlib.pyplot as plt

# Create collection and load methods
collection = LCMethodCollection()
lc_folder = Path("/Users/eileen.wang/Desktop/diann/SampleData/methods/LC")

collection.add_method('20min', str(lc_folder / '20m150nlv15.meth'))
collection.add_method('25min', str(lc_folder / '25m150nlv5.meth'))
collection.add_method('36min', str(lc_folder / '36m150nlLong40.meth'))

print(f"Loaded {len(collection)} methods")
print("=" * 80)

# Create a 1x2 subplot layout to compare single vs twin axes
fig, axes = plt.subplots(1, 2, figsize=(16, 6))

# Test 1: Plot multiple columns on same axis (without twin axes)
print("\n1. Plotting multiple columns on same axis:")
collection.plot_gradients(
    y_cols=['Neo.PumpModule.Pump.%B.Value [%]',
            'Neo.PumpModule.Pump.Flow.Nominal [µl/min]'],
    twin_axes=False,
    ax=axes[0]
)
axes[0].set_title('Same Axis (Hard to compare different scales)')
print("✓ Success")

# Test 2: Plot multiple columns with twin y-axes (different scales)
print("\n2. Plotting multiple columns with twin y-axes:")
twin_ax = collection.plot_gradients(
    y_cols=['Neo.PumpModule.Pump.%B.Value [%]',
            'Neo.PumpModule.Pump.Flow.Nominal [µl/min]'],
    twin_axes=True,
    ax=axes[1]
)
axes[1].set_title('Twin Y-Axes (Each column has its own scale)')
print(f"✓ Success - Returned {len(twin_ax)} axes")
print(f"  Axes: {twin_ax}")

plt.tight_layout()
plt.savefig('/tmp/lc_gradient_twin_axes.png', dpi=100)
print("\n✓ Saved plot to /tmp/lc_gradient_twin_axes.png")

# Test 3: Create standalone plot with twin axes
print("\n3. Standalone plot with twin y-axes:")
axes_tuple = collection.plot_gradients(
    method_names=['20min', '25min'],
    y_cols=['Neo.PumpModule.Pump.%B.Value [%]',
            'Neo.PumpModule.Pump.Flow.Nominal [µl/min]'],
    twin_axes=True,
    figsize=(10, 6)
)
plt.savefig('/tmp/lc_gradient_twin_axes_standalone.png', dpi=100)
plt.close()
print(f"✓ Success - Created plot with {len(axes_tuple)} axes")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("\nTwin Axes Feature:")
print("  - twin_axes=False: All columns plotted on same y-axis (default)")
print("  - twin_axes=True: Each column gets its own y-axis scale")
print("\nBenefits:")
print("  - Compare parameters with different units or scales")
print("  - %B (0-100%) vs Flow (µl/min) can be seen clearly")
print("  - Each axis has its own label and legend position")
print("\nReturn value:")
print("  - twin_axes=False: returns single axis")
print("  - twin_axes=True: returns tuple of (ax1, ax2, ...)")
print("=" * 80)
