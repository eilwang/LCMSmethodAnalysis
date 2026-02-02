# MS Method Collection - find_differences()

## Overview

The `find_differences()` method compares multiple MS methods and returns a **single unified DataFrame** with all differences together. Each difference is tagged with a Type to distinguish between instrument parameters, polarity parameters, and DIA settings.

## Return Format

Returns a single `pd.DataFrame` with columns:
- **Parameter**: Parameter name
- **Type**: Type of difference ('instrument_param', 'polarity_param', 'dia_stat', 'dia_window_param', 'dia_windows')
- **Description**: Human-readable description
- **[Method Names]**: One column per method with the values

## Usage

```python
from ms_method_collection import MSMethodCollection

collection = MSMethodCollection()
collection.add_methods_from_folder('/path/to/methods')

# Compare two methods
diff_df = collection.find_differences(['DIA007.proteoscape', 'DIA016.proteoscape'])

# Filter by type
instrument_diffs = diff_df[diff_df['Type'] == 'instrument_param']
dia_diffs = diff_df[diff_df['Type'].str.startswith('dia_')]
```

## Difference Types

### 1. instrument_param
Global MS instrument parameters that differ.

```python
instrument_diffs = diff_df[diff_df['Type'] == 'instrument_param']
```

Example output:
```
Parameter: Mode_ScanEnd
Type: instrument_param
DIA007.proteoscape: 1500.0
DIA016.proteoscape: 1250.0
```

### 2. polarity_param
Polarity-specific parameters (ESI, CaptivaSpray, APCI, etc.) that differ.

```python
polarity_diffs = diff_df[diff_df['Type'] == 'polarity_param']
```

Example output:
```
Parameter: default_Source_CapillarySetValue
Type: polarity_param
Description: positive polarity
DIA007.proteoscape: 4500.0
DIA016.proteoscape: 4300.0
```

### 3. dia_stat
DIA statistics that differ (window count, cycle count, m/z range, IM range).

```python
dia_stat_diffs = diff_df[diff_df['Type'] == 'dia_stat']
```

Example output:
```
Parameter: dia_mz_max
Type: dia_stat
Description: m/z maximum
DIA007.proteoscape: 1341.0
DIA016.proteoscape: 1199.99
```

Compares:
- `dia_window_count`: Number of DIA windows
- `dia_cycle_count`: Number of PASEF cycles
- `dia_mz_min`: Minimum m/z
- `dia_mz_max`: Maximum m/z
- `dia_im_min`: Minimum 1/K0
- `dia_im_max`: Maximum 1/K0

### 4. dia_window_param
Individual DIA window parameter differences (only when methods have the same number of windows).

```python
window_diffs = diff_df[diff_df['Type'] == 'dia_window_param']
```

Example output:
```
Parameter: window_1_MzStart
Type: dia_window_param
Description: Window 1 MzStart
DIA007.proteoscape: 741.34
DIA016.proteoscape: 729.34
```

Compares each window's:
- `MzStart`, `MzEnd`: m/z boundaries
- `OneOverK0Start`, `OneOverK0End`: Ion mobility boundaries
- `CycleId`: PASEF cycle assignment

### 5. dia_windows
Complete DIA window specifications as DataFrame objects (included when windows differ).

```python
windows_row = diff_df[diff_df['Type'] == 'dia_windows']
```

Example output:
```
Parameter: dia_windows
Type: dia_windows
Description: Complete DIA window specifications (DataFrame objects)
DIA007.proteoscape: <DataFrame shape (9, 11)>
DIA016.proteoscape: <DataFrame shape (9, 11)>
```

You can access the actual DataFrames:
```python
windows_row = diff_df[diff_df['Type'] == 'dia_windows'].iloc[0]
method1_windows = windows_row['DIA007.proteoscape']
method2_windows = windows_row['DIA016.proteoscape']

# Now you have the complete DIA window DataFrames
print(method1_windows.head())
```

## Parameters

```python
find_differences(
    method_names: Optional[List[str]] = None,
    include_params: bool = True,
    include_polarity_configs: bool = True,
    include_dia: bool = True,
    polarities: Optional[List[str]] = None,
    sources: Optional[List[str]] = None,
    tolerance: float = 1e-6
) -> pd.DataFrame
```

- **method_names**: Methods to compare. If None, compare all methods.
- **include_params**: Whether to check global MS instrument parameters (default: True)
- **include_polarity_configs**: Whether to check polarity-specific parameters (default: True)
- **include_dia**: Whether to check DIA settings (default: True)
- **polarities**: Specific polarities to compare ('positive', 'negative'). If None, compare all.
- **sources**: Specific ion sources to compare ('esi', 'captivespray', 'apci', etc.). If None, compare all.
- **tolerance**: Tolerance for floating point comparisons (default: 1e-6)

## Examples

### Compare All Settings

```python
# Compare all settings across all methods
diff_df = collection.find_differences()

# Show breakdown by type
print(diff_df['Type'].value_counts())
```

### Compare Specific Methods

```python
# Compare two specific methods
diff_df = collection.find_differences(['DIA007.proteoscape', 'DIA016.proteoscape'])

print(f"Total differences: {len(diff_df)}")
print(f"\nBy type:")
for diff_type in diff_df['Type'].unique():
    count = len(diff_df[diff_df['Type'] == diff_type])
    print(f"  {diff_type}: {count}")
```

### Compare Only DIA Settings

```python
# Focus only on DIA differences
diff_df = collection.find_differences(
    method_names=['DIA007.proteoscape', 'DIA016.proteoscape'],
    include_params=False,
    include_polarity_configs=False,
    include_dia=True
)

# Show DIA statistics differences
dia_stats = diff_df[diff_df['Type'] == 'dia_stat']
print(dia_stats)

# Show window parameter differences
window_params = diff_df[diff_df['Type'] == 'dia_window_param']
print(f"\n{len(window_params)} window parameters differ")
```

### Access Complete DIA Windows

```python
diff_df = collection.find_differences(['DIA007.proteoscape', 'DIA016.proteoscape'])

# Get the dia_windows row
windows_rows = diff_df[diff_df['Type'] == 'dia_windows']

if len(windows_rows) > 0:
    row = windows_rows.iloc[0]

    # Access the actual window DataFrames
    method1_windows = row['DIA007.proteoscape']
    method2_windows = row['DIA016.proteoscape']

    print("Method 1 windows:")
    print(method1_windows)

    print("\nMethod 2 windows:")
    print(method2_windows)

    # Compare specific columns
    print("\nMzStart comparison:")
    print(f"Method 1: {method1_windows['MzStart'].values}")
    print(f"Method 2: {method2_windows['MzStart'].values}")
```

### Filter to Specific Parameter Types

```python
diff_df = collection.find_differences()

# Get only instrument parameter differences
instrument = diff_df[diff_df['Type'] == 'instrument_param']

# Get only polarity parameter differences
polarity = diff_df[diff_df['Type'] == 'polarity_param']

# Get all DIA-related differences
dia_all = diff_df[diff_df['Type'].str.startswith('dia_')]

# Get just DIA statistics (not window-by-window)
dia_stats_only = diff_df[diff_df['Type'] == 'dia_stat']

# Get just window parameter differences
window_params_only = diff_df[diff_df['Type'] == 'dia_window_param']
```

### Export to CSV

```python
diff_df = collection.find_differences(['method1', 'method2'])

# Export to CSV (note: dia_windows DataFrames won't export well)
# Filter out dia_windows type first
export_df = diff_df[diff_df['Type'] != 'dia_windows']
export_df.to_csv('method_differences.csv', index=False)
```

## DIA Comparison Details

The DIA comparison is comprehensive:

1. **Basic Statistics** (Type: 'dia_stat')
   - Window count, cycle count
   - m/z range (min/max)
   - Ion mobility range (min/max)

2. **Window-by-Window** (Type: 'dia_window_param')
   - Only performed if methods have the same number of windows
   - Compares each window's m/z boundaries, IM boundaries, and cycle assignment
   - Each difference gets its own row

3. **Complete Windows** (Type: 'dia_windows')
   - Included when windows differ
   - Contains the complete DIA window DataFrames for detailed inspection
   - Useful for understanding the full window scheme

## Return Format Details

```python
diff_df = collection.find_differences(['method1', 'method2'])

# DataFrame structure:
# Parameter | Type | Description | method1 | method2
# ----------|------|-------------|---------|--------
# Mode_ScanEnd | instrument_param | | 1500.0 | 1250.0
# default_Source_CapillarySetValue | polarity_param | positive polarity | 4500.0 | 4300.0
# dia_mz_max | dia_stat | m/z maximum | 1341.0 | 1199.99
# window_1_MzStart | dia_window_param | Window 1 MzStart | 741.34 | 729.34
# dia_windows | dia_windows | Complete DIA window specifications | <DataFrame> | <DataFrame>
```

## Key Features

1. **Single DataFrame**: All differences in one place, easy to filter and analyze
2. **Type Column**: Distinguish between different parameter types
3. **Comprehensive DIA**: Full comparison including window-by-window and complete DataFrames
4. **Filterable**: Easy to filter by type using pandas
5. **Exportable**: Can export to CSV (except dia_windows DataFrames)
