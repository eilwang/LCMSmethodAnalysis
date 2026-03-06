# MS Method Flat Dictionary Access

## Summary

The `MSMethodCollection` returns a **flat dictionary** when you access methods, making parameter access simple and intuitive. All parameters are at the top level - no nested `.ms` or `.dia` attributes!

**Key Features:**
- All parameters at top level (no `.ms.params` needed)
- Only positive polarity values (no nested polarity dicts)
- Direct access to DIA windows and settings
- File and general info included with prefixes

## Simple Example

**Clean and simple access:**
```python
method = collection['method_name']  # Returns flat dict!
value = method['Collision_GasSupply_Set']
cap_voltage = method['default_Source_CapillarySetValue']  # Positive only
windows = method['dia_windows']
```

**That's it!** No nested `.ms.params` or `.dia.windows` - just direct dictionary access.

## Structure

### What's Included

The flat dictionary contains:

1. **File Info** (prefixed with `fileinfo_`)
   - `fileinfo_type`, `fileinfo_createdate`, `fileinfo_appname`, etc.

2. **General Info** (prefixed with `generalinfo_`)
   - `generalinfo_org`, `generalinfo_hostname`, `generalinfo_author`, etc.

3. **Global MS Parameters** (no prefix)
   - `Collision_GasSupply_Set`, `TOF_DetectorTofSetValue`, etc.

4. **Polarity-Specific Parameters** (source prefix, positive values only)
   - `default_Source_CapillarySetValue`, `esi_Transfer_CapillaryExit_Base_Set`, etc.
   - **Only positive polarity values are included** (no nested dicts)

5. **DIA Information**
   - `has_dia` (boolean)
   - `dia_windows` (DataFrame of all windows)
   - `dia_global_info` (dict)
   - `dia_window_count`, `dia_mz_min`, `dia_mz_max`, `dia_im_min`, `dia_im_max`
   - `dia_cycle_count`

6. **Synchro Information**
   - `has_synchro` (boolean)

## Usage Examples

### 1. Basic Access

```python
from ms_method_collection import MSMethodCollection

# Load methods
collection = MSMethodCollection()
collection.add_methods_from_folder('/path/to/methods')

# Get method as flat dictionary
method = collection['DIA011RT70expandedrange.proteoscape']

print(f"Type: {type(method)}")  # <class 'dict'>
print(f"Keys: {len(method)}")   # ~436 parameters
```

### 2. Access MS Parameters

```python
# Global parameters - direct access!
gas_supply = method['Collision_GasSupply_Set']
tof_value = method['TOF_DetectorTofSetValue']
sample_interval = method['Digitizer_SampleIntervall']

print(f"Collision Gas: {gas_supply}")
print(f"TOF Detector: {tof_value}")
print(f"Sample Interval: {sample_interval}")
```

### 3. Access Polarity-Specific Parameters

Only positive polarity values are included (no nested dicts!):

```python
# These now return single values, not dicts
bias = method['default_Collision_Bias_Set']  # Just the positive value
cap_voltage = method.get('default_Source_CapillarySetValue')  # Positive only

print(f"Collision Bias (positive): {bias}")
print(f"Capillary Voltage (positive): {cap_voltage}")
```

### 4. Access DIA Windows

```python
# Check if method has DIA
if method['has_dia']:
    # Get DIA windows DataFrame directly
    windows = method['dia_windows']
    print(f"Window count: {method['dia_window_count']}")
    print(f"m/z range: {method['dia_mz_min']:.1f} - {method['dia_mz_max']:.1f}")
    print(f"IM range: {method['dia_im_min']:.2f} - {method['dia_im_max']:.2f}")

    # Work with windows DataFrame
    dia_only = windows[windows['Type'] == 1]  # MS2/DIA windows only
    print(f"DIA windows shape: {dia_only.shape}")
```

### 5. Access File/General Info

```python
# File metadata (prefixed with fileinfo_)
created = method['fileinfo_createdate']
app_version = method['fileinfo_appversion']

# General info (prefixed with generalinfo_)
hostname = method['generalinfo_hostname']
org = method['generalinfo_org']

print(f"Created: {created}")
print(f"Hostname: {hostname}")
print(f"Organization: {org}")
```

### 6. Iterate Through All Parameters

```python
# Easy iteration - it's just a dict!
for key, value in method.items():
    if not key.startswith('dia_') and not key.startswith('has_'):
        print(f"{key}: {value}")
```

### 7. Export to DataFrame

```python
import pandas as pd

# Convert to DataFrame for analysis
rows = []
for method_name in collection.list_methods():
    method = collection[method_name]
    row = {
        'Method': method_name,
        'Collision_Gas': method['Collision_GasSupply_Set'],
        'TOF_Detector': method['TOF_DetectorTofSetValue'],
        'Has_DIA': method['has_dia'],
        'Window_Count': method.get('dia_window_count', 0)
    }
    rows.append(row)

df = pd.DataFrame(rows)
print(df)
```

### 8. Compare Methods Easily

```python
# Compare parameters across methods
methods = ['DIA011.proteoscape', 'DIA015.proteoscape']

for param in ['Collision_GasSupply_Set', 'TOF_DetectorTofSetValue']:
    print(f"\n{param}:")
    for method_name in methods:
        method = collection[method_name]
        print(f"  {method_name}: {method[param]}")
```

## Structure Benefits

The flat dictionary is:

1. **Simple**: Just use `collection['method_name']` and you get a dictionary
2. **Direct**: Access any parameter with `method['param_name']`
3. **Clean**: No nested `.ms.params` or `.dia.windows` paths
4. **Intuitive**: Works like any Python dictionary
5. **Fast**: No nested attribute lookups

## Key Features

1. **Flat Dictionary**: All parameters at top level, no nested `.ms` or `.dia`
2. **Positive Polarity Only**: Polarity-specific params return single values (positive mode)
3. **Prefixed Metadata**: File/general info use prefixes (`fileinfo_`, `generalinfo_`)
4. **DIA Stats Included**: Window counts, ranges pre-calculated for convenience
5. **Still Pandas**: DIA windows returned as DataFrame for easy manipulation
6. **436 Parameters**: Everything you need in one dictionary
