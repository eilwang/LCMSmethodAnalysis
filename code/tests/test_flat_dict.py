"""Test the new flat dictionary structure for MS methods."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from LCMSmethodAnalysis.parsers.timsmeth.ms_method_collection import MicroTOFMethodCollection

print("Testing Flat Dictionary Structure")
print("=" * 80)

# Load collection
collection = MicroTOFMethodCollection()
methods_folder = "/Users/eileen.wang/Desktop/diann/SampleData/methods/MS"
collection.add_methods_from_folder(methods_folder)

print(f"\nLoaded {len(collection)} methods")

# Get first method as flat dict
method_name = collection.list_methods()[0]
print(f"\nMethod: {method_name}")
print("=" * 80)

# Access method - now returns a flat dictionary!
method_dict = collection[method_name]

print(f"\n1. Type returned: {type(method_dict)}")
print(f"   Dictionary keys: {len(method_dict)}")

# Show direct access to parameters (no .ms or .dia needed!)
print(f"\n2. Direct parameter access (positive polarity only):")

# Global parameters
print(f"   Collision_GasSupply_Set: {method_dict.get('Collision_GasSupply_Set')}")
print(f"   TOF_DetectorTofSetValue: {method_dict.get('TOF_DetectorTofSetValue')}")

# Polarity-specific parameters (only positive values included)
print(f"   default_Source_CapillarySetValue: {method_dict.get('default_Source_CapillarySetValue')}")
print(f"   default_Collision_Bias_Set: {method_dict.get('default_Collision_Bias_Set')}")

# File info
print(f"\n3. File info (prefixed):")
print(f"   fileinfo_type: {method_dict.get('fileinfo_type')}")
print(f"   fileinfo_createdate: {method_dict.get('fileinfo_createdate')}")

# General info
print(f"\n4. General info (prefixed):")
print(f"   generalinfo_org: {method_dict.get('generalinfo_org')}")
print(f"   generalinfo_hostname: {method_dict.get('generalinfo_hostname')}")

# DIA information
print(f"\n5. DIA information:")
print(f"   has_dia: {method_dict.get('has_dia')}")
if method_dict.get('has_dia'):
    print(f"   dia_window_count: {method_dict.get('dia_window_count')}")
    print(f"   dia_mz_range: {method_dict.get('dia_mz_min'):.1f} - {method_dict.get('dia_mz_max'):.1f}")
    print(f"   dia_im_range: {method_dict.get('dia_im_min'):.2f} - {method_dict.get('dia_im_max'):.2f}")
    print(f"   dia_cycle_count: {method_dict.get('dia_cycle_count')}")

    # Access DIA windows DataFrame
    dia_windows = method_dict['dia_windows']
    print(f"\n   DIA windows DataFrame shape: {dia_windows.shape}")
    print(f"   First few windows:")
    print(dia_windows.head(3))

# Demonstrate iteration over all parameters
print(f"\n6. All parameters (first 20):")
count = 0
for key, value in method_dict.items():
    if count < 20 and not key.startswith('dia_') and not key.startswith('has_'):
        val_str = str(value)[:60] + '...' if len(str(value)) > 60 else str(value)
        print(f"   {key}: {val_str}")
        count += 1

print(f"\n{'='*80}")
print("✓ Flat dictionary structure test complete!")
print(f"{'='*80}")

# Show simple access pattern
print(f"\nSimple access pattern:")
print("  method = collection['method_name']  # Returns flat dict")
print("  value = method['Collision_GasSupply_Set']  # Direct access!")
print("  windows = method['dia_windows']  # Direct access!")
print("  # That's it! No nested .ms or .dia needed!")
