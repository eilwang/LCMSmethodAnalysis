# MS Method Collection - Quick Start

## Simple 3-Step Access

```python
from ms_method_collection import MSMethodCollection

# 1. Load methods
collection = MSMethodCollection()
collection.add_methods_from_folder('/path/to/methods')

# 2. Get method (returns flat dict!)
method = collection['DIA011RT70expandedrange.proteoscape']

# 3. Access any parameter directly
gas_supply = method['Collision_GasSupply_Set']
tof_detector = method['TOF_DetectorTofSetValue']
windows = method['dia_windows']
```

That's it! No nested `.ms` or `.dia` - just direct dictionary access.

## What You Get

When you access a method with `collection['method_name']`, you get a dictionary with **436 parameters**:

- **Global MS parameters** (no prefix)
  - `Collision_GasSupply_Set`, `TOF_DetectorTofSetValue`, etc.

- **Polarity-specific parameters** (source prefix, positive values only)
  - `default_Collision_Bias_Set`, `esi_Source_CapillarySetValue`, etc.

- **File metadata** (`fileinfo_` prefix)
  - `fileinfo_createdate`, `fileinfo_appversion`, etc.

- **General info** (`generalinfo_` prefix)
  - `generalinfo_hostname`, `generalinfo_org`, etc.

- **DIA information**
  - `dia_windows` (DataFrame), `dia_window_count`, `dia_mz_min`, `dia_mz_max`, etc.

## Common Operations

### Access MS Parameters

```python
# Direct access - it's just a dict!
gas = method['Collision_GasSupply_Set']
tof = method['TOF_DetectorTofSetValue']
bias = method['default_Collision_Bias_Set']  # Positive polarity
```

### Work with DIA Windows

```python
if method['has_dia']:
    windows = method['dia_windows']  # DataFrame
    print(f"Windows: {method['dia_window_count']}")
    print(f"m/z: {method['dia_mz_min']:.1f} - {method['dia_mz_max']:.1f}")

    # Filter to DIA windows only
    dia_only = windows[windows['Type'] == 1]
```

### Compare Methods

```python
methods = ['DIA011.proteoscape', 'DIA015.proteoscape']

for param in ['Collision_GasSupply_Set', 'dia_window_count']:
    print(f"\n{param}:")
    for name in methods:
        method = collection[name]
        print(f"  {name}: {method[param]}")
```

### Export to DataFrame

```python
import pandas as pd

rows = []
for name in collection.list_methods():
    method = collection[name]
    rows.append({
        'Method': name,
        'Collision_Gas': method['Collision_GasSupply_Set'],
        'TOF': method['TOF_DetectorTofSetValue'],
        'Windows': method.get('dia_window_count', 0)
    })

df = pd.DataFrame(rows)
```

### Iterate All Parameters

```python
# It's just a dict - iterate like any dict!
for key, value in method.items():
    print(f"{key}: {value}")
```

## Key Points

1. **Returns Dictionary**: `collection[name]` gives you a plain Python `dict`
2. **All at Top Level**: No nested `.ms.params` or `.dia.windows`
3. **Positive Polarity**: Only positive values for polarity-specific params
4. **436 Parameters**: Everything in one place
5. **Simple Access**: `method['param_name']` - that's it!

## Loading Methods

```python
# From folder
collection.add_methods_from_folder('/path/to/methods')

# From zip file
collection.add_methods_from_folder('/path/to/methods.zip')

# Single method
collection.add_method('/path/to/method.m', name='my_method')

# List methods
methods = collection.list_methods()
print(f"Loaded {len(collection)} methods")
```

## Full Example

```python
from ms_method_collection import MSMethodCollection

# Load methods
collection = MSMethodCollection()
collection.add_methods_from_folder('/Users/user/methods')

# Get method as flat dict
method = collection['DIA011.proteoscape']

# Access MS parameters
print(f"Collision Gas: {method['Collision_GasSupply_Set']}")
print(f"TOF Detector: {method['TOF_DetectorTofSetValue']}")

# Access DIA info
if method['has_dia']:
    windows = method['dia_windows']
    print(f"\nDIA Windows: {len(windows)}")
    print(f"m/z range: {method['dia_mz_min']:.1f} - {method['dia_mz_max']:.1f}")
    print(f"\nWindow details:")
    print(windows.head())

# Compare across methods
print(f"\nCollision Gas across methods:")
for name in collection.list_methods()[:5]:
    m = collection[name]
    print(f"  {name}: {m['Collision_GasSupply_Set']}")
```

Clean, simple, and intuitive! 🎉
