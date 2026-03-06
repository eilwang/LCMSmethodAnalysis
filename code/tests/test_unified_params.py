"""Test the unified params structure in MicroTOFMethod."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from LCMSmethodAnalysis.parsers.timsmeth.ms_method_collection import MicroTOFMethodCollection

print("Testing Unified Params Structure")
print("=" * 80)

# Load collection
collection = MicroTOFMethodCollection()
methods_folder = "/Users/eileen.wang/Desktop/diann/SampleData/methods/MS"
collection.add_methods_from_folder(methods_folder)

print(f"\nLoaded {len(collection)} methods")

# Get first method
method_name = collection.list_methods()[0]
method = collection[method_name]

print(f"\n{'='*80}")
print(f"Method: {method_name}")
print(f"{'='*80}")

# Test unified params structure
print(f"\n1. Unified params dictionary:")
print(f"   Total parameters: {len(method.ms.params)}")

# Count parameter types
global_count = sum(1 for v in method.ms.params.values() if not isinstance(v, dict))
polarity_count = sum(1 for v in method.ms.params.values() if isinstance(v, dict))

print(f"   Global parameters: {global_count}")
print(f"   Polarity-specific parameters: {polarity_count}")

# Show some global parameters
print(f"\n2. Example global parameters (first 5):")
count = 0
for name, value in method.ms.params.items():
    if not isinstance(value, dict) and count < 5:
        val_str = str(value)[:60] + '...' if len(str(value)) > 60 else str(value)
        print(f"   {name}: {val_str}")
        count += 1

# Show some polarity-specific parameters
print(f"\n3. Example polarity-specific parameters (first 5):")
count = 0
for name, value in method.ms.params.items():
    if isinstance(value, dict) and count < 5:
        print(f"   {name}:")
        for polarity, pol_value in value.items():
            val_str = str(pol_value)[:50] + '...' if len(str(pol_value)) > 50 else str(pol_value)
            print(f"     {polarity}: {val_str}")
        count += 1

# Test get_param method
print(f"\n4. Testing get_param() method:")

# Global parameter
gas_supply = method.get_param('Collision_GasSupply_Set')
print(f"   Global param (Collision_GasSupply_Set): {gas_supply}")

# Polarity-specific parameter
# Find a polarity-specific param to test
test_param = None
for name in method.ms.params:
    if isinstance(method.ms.params[name], dict) and '_' in name:
        source, param_name = name.split('_', 1)
        test_param = (source, param_name)
        break

if test_param:
    source, param_name = test_param
    val_pos = method.get_param(param_name, polarity='positive', source=source)
    val_neg = method.get_param(param_name, polarity='negative', source=source)
    print(f"   Polarity param ({source}_{param_name}):")
    print(f"     positive: {val_pos}")
    print(f"     negative: {val_neg}")

# Test comparison across methods if we have multiple
if len(collection) > 1:
    print(f"\n5. Testing comparison across methods:")
    method1_name = collection.list_methods()[0]
    method2_name = collection.list_methods()[1]

    differences = collection.find_differences([method1_name, method2_name])

    print(f"   Comparing: {method1_name} vs {method2_name}")
    print(f"   Methods identical: {differences['identical']}")
    print(f"   Global param differences: {len(differences['param_differences_df'])}")
    print(f"   Polarity param differences: {len(differences['polarity_differences_df'])}")

print(f"\n{'='*80}")
print("✓ Unified params structure test complete!")
print(f"{'='*80}")
