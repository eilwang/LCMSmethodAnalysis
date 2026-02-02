# MSMethodCollection.to_dataframe()

## Quick Reference

Convert MS methods to a pandas DataFrame for easy analysis, comparison, and export.

## Basic Usage

```python
from ms_method_collection import MSMethodCollection

collection = MSMethodCollection()
collection.add_methods_from_folder('/path/to/methods')

# Get all methods and parameters
df = collection.to_dataframe()

# Returns DataFrame with:
#   - Rows: Methods (46 methods)
#   - Columns: Parameters (435 parameters)
#   - Values: Parameter values
```

## Parameters

```python
to_dataframe(
    method_names: Optional[List[str]] = None,
    param_names: Optional[List[str]] = None,
    exclude_dia_windows: bool = True
) -> pd.DataFrame
```

- **method_names**: List of methods to include (default: all methods)
- **param_names**: List of parameters to include (default: all parameters)
- **exclude_dia_windows**: Exclude `dia_windows` DataFrame objects (default: True)

## Examples

### 1. Full DataFrame

```python
# All methods, all parameters
df = collection.to_dataframe()

print(f"Shape: {df.shape}")  # (46 methods, 435 parameters)
print(df.head())
```

Output:
```
                          fileinfo_type  Collision_GasSupply_Set  dia_window_count
DIA003.proteoscape  ImpacTEM Pro Method                     58.0              16.0
DIA015.proteoscape  ImpacTEM Pro Method                     58.0              48.0
DIA007.proteoscape  ImpacTEM Pro Method                     58.0               8.0
```

### 2. Specific Methods

```python
# Compare just 3 methods
df = collection.to_dataframe(
    method_names=['DIA007.proteoscape', 'DIA016.proteoscape', 'DIA018.proteoscape']
)

print(df.shape)  # (3 methods, 435 parameters)
```

### 3. Specific Parameters

```python
# Get specific parameters across all methods
params = [
    'Collision_GasSupply_Set',
    'TOF_DetectorTofSetValue',
    'dia_window_count',
    'dia_mz_min',
    'dia_mz_max'
]

df = collection.to_dataframe(param_names=params)

print(df)
```

Output:
```
                          Collision_GasSupply_Set  TOF_DetectorTofSetValue  dia_window_count
DIA003.proteoscape                          58.0                   8050.0              16.0
DIA015.proteoscape                          58.0                   8050.0              48.0
DIA007.proteoscape                          58.0                   8050.0               8.0
...
```

### 4. Subset Both Methods and Parameters

```python
# Compare specific parameters for specific methods
df = collection.to_dataframe(
    method_names=['DIA007.proteoscape', 'DIA016.proteoscape'],
    param_names=['Collision_GasSupply_Set', 'dia_window_count', 'dia_mz_max']
)

print(df)
```

Output:
```
                    Collision_GasSupply_Set  dia_window_count  dia_mz_max
DIA007.proteoscape                     58.0               8.0     1341.00
DIA016.proteoscape                     58.0               8.0     1199.99
```

### 5. Filter After Creation

```python
# Get full DataFrame, then filter
df = collection.to_dataframe()

# Filter to DIA-related parameters
dia_cols = [col for col in df.columns if col.startswith('dia_')]
df_dia = df[dia_cols]

# Filter to specific methods
methods = ['DIA007.proteoscape', 'DIA016.proteoscape']
df_subset = df.loc[methods]

# Both at once
df_final = df.loc[methods, dia_cols]
```

### 6. Export to CSV/Excel

```python
# Export all methods and parameters
df = collection.to_dataframe()
df.to_csv('method_parameters.csv')
df.to_excel('method_parameters.xlsx')

# Export subset
df_subset = collection.to_dataframe(
    method_names=['DIA007.proteoscape', 'DIA016.proteoscape'],
    param_names=['Collision_GasSupply_Set', 'dia_window_count']
)
df_subset.to_csv('method_comparison.csv')
```

### 7. Quick Comparison

```python
# Find parameters that differ between two methods
df = collection.to_dataframe(
    method_names=['DIA007.proteoscape', 'DIA016.proteoscape']
)

differences = []
for param in df.columns:
    val1 = df.loc['DIA007.proteoscape', param]
    val2 = df.loc['DIA016.proteoscape', param]

    if val1 != val2:
        # Skip NaN comparisons
        if not (pd.isna(val1) and pd.isna(val2)):
            differences.append(param)

print(f"Found {len(differences)} differences")
print(differences[:10])
```

### 8. Statistical Analysis

```python
import numpy as np

# Get numeric parameters
df = collection.to_dataframe()
numeric_df = df.select_dtypes(include=[np.number])

# Calculate statistics
print(numeric_df.describe())

# Find parameters with variance
variance = numeric_df.var()
print(variance.sort_values(ascending=False).head(10))

# Check if parameter is constant across methods
constant_params = numeric_df.columns[numeric_df.nunique() == 1]
print(f"Constant parameters: {len(constant_params)}")
```

### 9. Include DIA Windows DataFrames

```python
# Include dia_windows (DataFrame objects)
df = collection.to_dataframe(
    method_names=['DIA007.proteoscape', 'DIA016.proteoscape'],
    param_names=['dia_window_count', 'dia_windows'],
    exclude_dia_windows=False  # Include DataFrame objects
)

# Access the actual DIA windows DataFrame
windows = df.loc['DIA007.proteoscape', 'dia_windows']
print(f"Type: {type(windows)}")  # <class 'pandas.core.frame.DataFrame'>
print(windows.head())
```

### 10. Pattern Matching Parameters

```python
# Get all TOF-related parameters
df = collection.to_dataframe()
tof_params = [col for col in df.columns if 'TOF' in col]
df_tof = df[tof_params]

# Get all calibration parameters
cal_params = [col for col in df.columns if 'Calibration' in col]
df_cal = df[cal_params]

# Get all source-related parameters
source_params = [col for col in df.columns if any(
    x in col for x in ['esi_', 'apci_', 'captivespray_']
)]
df_source = df[source_params]
```

## Common Workflows

### Workflow 1: Find Methods with Specific Settings

```python
# Find all methods with >20 DIA windows
df = collection.to_dataframe(param_names=['dia_window_count'])
high_window_methods = df[df['dia_window_count'] > 20].index.tolist()

print(f"Methods with >20 windows: {high_window_methods}")
```

### Workflow 2: Compare DIA Settings

```python
# Compare DIA settings across all methods
dia_params = ['dia_window_count', 'dia_cycle_count', 'dia_mz_min', 'dia_mz_max']
df = collection.to_dataframe(param_names=dia_params)

# Sort by window count
df_sorted = df.sort_values('dia_window_count')
print(df_sorted)

# Group by window count
counts = df.groupby('dia_window_count').size()
print(f"\nMethods by window count:\n{counts}")
```

### Workflow 3: Identify Unique Configurations

```python
# Find unique combinations of key parameters
key_params = ['Collision_GasSupply_Set', 'TOF_DetectorTofSetValue', 'dia_window_count']
df = collection.to_dataframe(param_names=key_params)

# Find unique combinations
unique_configs = df.drop_duplicates()
print(f"Found {len(unique_configs)} unique configurations")
print(unique_configs)
```

### Workflow 4: Batch Analysis

```python
# Analyze all methods in batches
df = collection.to_dataframe()

# Group methods by some criterion
df['has_many_windows'] = df['dia_window_count'] > 15

# Compare groups
high_window = df[df['has_many_windows']]
low_window = df[~df['has_many_windows']]

print(f"High window methods: {len(high_window)}")
print(f"Low window methods: {len(low_window)}")

# Compare parameter distributions
for param in ['Collision_GasSupply_Set', 'Mode_ScanEnd']:
    print(f"\n{param}:")
    print(f"  High: {high_window[param].unique()}")
    print(f"  Low: {low_window[param].unique()}")
```

## vs find_differences()

**Use `to_dataframe()` when:**
- You want flexible DataFrame access
- You need to export data
- You're doing statistical analysis
- You want to filter/subset manually

**Use `find_differences()` when:**
- You want automated difference detection
- You need tolerance-based float comparison
- You want comprehensive DIA window comparison
- You want structured output with Type column

**Best of both worlds:**
```python
# 1. Use DataFrame to identify interesting methods
df = collection.to_dataframe(param_names=['dia_window_count'])
interesting = df[df['dia_window_count'] > 20].index.tolist()

# 2. Use find_differences for detailed comparison
diff_df = collection.find_differences(
    method_names=interesting,
    include_dia=True
)
print(diff_df)
```

## Performance

- **Memory**: ~20,000 values for 46 methods × 435 params (manageable)
- **Speed**: Fast for DataFrame operations, slower for initial creation
- **Tip**: If you have 1000+ methods, consider subsetting with `method_names`

## Notes

- Parameters are flattened (positive polarity only)
- `dia_windows` excluded by default (they're DataFrame objects)
- Returns empty DataFrame if collection is empty
- All 436 parameters available (435 + dia_windows if included)
