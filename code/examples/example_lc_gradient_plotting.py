"""
Example: Flexible gradient plotting with custom x and y axis selection
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lc_method_collection import VNeoMethodCollection
import matplotlib.pyplot as plt

# Create collection and load methods
collection = VNeoMethodCollection()
lc_folder = Path("/Users/eileen.wang/Desktop/diann/SampleData/methods/LC")

collection.add_method('20min', str(lc_folder / '20m150nlv15.meth'))
collection.add_method('25min', str(lc_folder / '25m150nlv5.meth'))
collection.add_method('36min', str(lc_folder / '36m150nlLong40.meth'))

print(f"Loaded {len(collection)} methods")
print("=" * 80)

# Create a 2x2 subplot layout to demonstrate different plotting options
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# Test 1: Default plot (time vs %B)
print("\n1. Default plot (time vs %B):")
collection.plot_gradients(ax=axes[0, 0])
axes[0, 0].set_title('Default: Time vs %B')
print("✓ Success")

# Test 2: Custom y-axis (time vs flow rate)
print("\n2. Custom y-axis (time vs flow rate):")
collection.plot_gradients(
    y_cols='Neo.PumpModule.Pump.Flow.Nominal [µl/min]',
    ax=axes[0, 1]
)
axes[0, 1].set_title('Time vs Flow Rate')
print("✓ Success")

# Test 3: Multiple y-axes on same plot
print("\n3. Multiple y-columns (time vs %B and Flow):")
collection.plot_gradients(
    y_cols=['Neo.PumpModule.Pump.%B.Value [%]',
            'Neo.PumpModule.Pump.Flow.Nominal [µl/min]'],
    ax=axes[1, 0]
)
axes[1, 0].set_title('Time vs Multiple Parameters')
print("✓ Success")

# Test 4: Custom x and y axes (%B vs Flow - phase diagram style)
print("\n4. Custom x and y axes (%B vs Flow):")
collection.plot_gradients(
    x_col='Neo.PumpModule.Pump.%B.Value [%]',
    y_cols='Neo.PumpModule.Pump.Flow.Nominal [µl/min]',
    ax=axes[1, 1]
)
axes[1, 1].set_title('%B vs Flow Rate (Phase Diagram)')
print("✓ Success")

plt.tight_layout()
plt.savefig('/tmp/lc_gradient_flexible_plotting.png', dpi=100)
print("\n✓ Saved plot to /tmp/lc_gradient_flexible_plotting.png")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("\nFlexible Plotting Features:")
print("  1. plot_gradients() - Now supports custom x and y axis selection")
print("  2. x_col parameter - Choose any column for x-axis (default: time)")
print("  3. y_cols parameter - Single or multiple columns for y-axis")
print("  4. ax parameter - Integration with matplotlib subplots")
print("\nExamples:")
print("  - Time vs %B (default)")
print("  - Time vs Flow")
print("  - Time vs multiple parameters")
print("  - %B vs Flow (phase diagram)")
print("=" * 80)
