"""Test the fixed plot_differences method."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ms_method_collection import MicroTOFMethodCollection
import matplotlib.pyplot as plt

print("Testing Fixed plot_differences() Method")
print("=" * 80)

# Load collection
collection = MicroTOFMethodCollection()
methods_folder = "/Users/eileen.wang/Desktop/diann/SampleData/methods/MS"
collection.add_methods_from_folder(methods_folder)

print(f"\nLoaded {len(collection)} methods")

# Test with methods that have differences
test_methods = ['DIA007.proteoscape', 'DIA016.proteoscape', 'DIA018.proteoscape']

print(f"\nTesting plot_differences with methods: {test_methods}")

try:
    fig = collection.plot_differences(method_names=test_methods)

    if fig is not None:
        print("✓ plot_differences executed successfully!")
        print(f"  Figure created: {type(fig)}")

        # Save the figure to verify
        output_path = "/Users/eileen.wang/Desktop/diann/code/tests/test_plot_differences.png"
        fig.savefig(output_path, dpi=100, bbox_inches='tight')
        print(f"  Saved plot to: {output_path}")
        plt.close(fig)
    else:
        print("✗ plot_differences returned None")

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

# Test with specific parameters
print(f"\n{'='*80}")
print("Testing with specific parameters")
specific_params = ['Collision_GasSupply_Set', 'TOF_DetectorTofSetValue', 'Mode_ScanEnd']

try:
    fig = collection.plot_differences(
        method_names=test_methods,
        param_names=specific_params
    )

    if fig is not None:
        print("✓ plot_differences with param_names executed successfully!")
        output_path = "/Users/eileen.wang/Desktop/diann/code/tests/test_plot_differences_specific.png"
        fig.savefig(output_path, dpi=100, bbox_inches='tight')
        print(f"  Saved plot to: {output_path}")
        plt.close(fig)
    else:
        print("✗ plot_differences returned None (no differences in specified params)")

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

print(f"\n{'='*80}")
print("✓ plot_differences fix test complete!")
print(f"{'='*80}")
