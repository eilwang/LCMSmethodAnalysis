"""
Example: Comparing LC gradients using enhanced comparison features
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from LCMSmethodAnalysis.parsers.vneometh.lc_method_collection import VNeoMethodCollection
import matplotlib.pyplot as plt

# Create collection and load methods
collection = VNeoMethodCollection()
lc_folder = Path("/Users/eileen.wang/Desktop/diann/SampleData/methods/LC")

# Add a few methods
collection.add_method('20min', str(lc_folder / '20m150nlv15.meth'))
collection.add_method('25min', str(lc_folder / '25m150nlv5.meth'))
collection.add_method('36min', str(lc_folder / '36m150nlLong40.meth'))

print(f"Loaded {len(collection)} methods")
print("=" * 80)

# Test 1: Basic gradient comparison (long format)
print("\n1. Basic gradient comparison (long format):")
print("-" * 80)
gradients_long = collection.compare_gradients()
print(f"Shape: {gradients_long.shape}")
print(gradients_long.head(10))

# Test 2: Wide format comparison (side-by-side)
print("\n2. Wide format comparison (side-by-side):")
print("-" * 80)
gradients_wide = collection.compare_gradients_wide()
print(f"Available columns: {list(gradients_wide.keys())}")

# Show %B comparison
if 'Neo.PumpModule.Pump.%B.Value [%]' in gradients_wide:
    print("\n%B Comparison:")
    print(gradients_wide['Neo.PumpModule.Pump.%B.Value [%]'].head(10))

# Test 3: Plot gradients
print("\n3. Plotting gradients:")
print("-" * 80)
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Plot %B gradient
ax1 = collection.plot_gradients(
    y_cols='Neo.PumpModule.Pump.%B.Value [%]',
    ax=axes[0]
)
axes[0].set_title('Gradient Comparison (%B)')

# Plot flow rate if available
if 'Neo.PumpModule.Pump.Flow.Nominal [µl/min]' in collection.methods['20min'].gradient.columns:
    ax2 = collection.plot_gradients(
        y_cols='Neo.PumpModule.Pump.Flow.Nominal [µl/min]',
        ax=axes[1]
    )
    axes[1].set_title('Flow Rate Comparison')

plt.tight_layout()
plt.savefig('/tmp/lc_gradient_comparison.png', dpi=100)
print("✓ Saved plot to /tmp/lc_gradient_comparison.png")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("\nNew LC Collection Features:")
print("  1. compare_gradients() - Combined gradients in long format")
print("  2. compare_gradients_wide() - Side-by-side comparison by column")
print("  3. plot_gradients() - Visual overlay of gradient profiles")
print("=" * 80)
