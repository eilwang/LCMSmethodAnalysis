# MSMethodCollection: DataFrame vs Dict Approach

## Overview

`MSMethodCollection` now offers two complementary approaches for accessing and comparing methods:

1. **Dict-based access**: `collection['method_name']` returns flat dict
2. **DataFrame-based access**: `collection.to_dataframe()` returns DataFrame

## When to Use Each

### Use Dict Access When:

```python
method = collection['method_name']
```

**Best for:**
- Accessing a single method's parameters
- Need access to complex objects (like `dia_windows` DataFrames)
- Writing scripts that process methods individually
- Fast single-parameter lookups

**Example:**
```python
# Get a specific parameter from one method
method = collection['DIA007.proteoscape']
gas_supply = method['Collision_GasSupply_Set']
windows = method['dia_windows']  # Get the full DIA windows DataFrame
```

### Use DataFrame Access When:

```python
df = collection.to_dataframe()
```

**Best for:**
- Comparing many methods at once
- Statistical analysis across methods
- Exporting to CSV/Excel
- Quick visual inspection
- Filtering by parameters
- Bulk comparisons

**Example:**
```python
# Compare parameters across multiple methods
df = collection.to_dataframe()

# Easy filtering
dia_params = df[[col for col in df.columns if col.startswith('dia_')]]

# Quick comparison
subset = df.loc[['method1', 'method2'], ['param1', 'param2']]

# Export
df.to_csv('method_comparison.csv')
```

## Efficiency Comparison

### find_differences()

The current `find_differences()` method:
- **Uses**: Dict-based approach internally
- **Efficient for**: Comprehensive comparisons with tolerance handling
- **Features**:
  - Float tolerance for comparisons
  - Comprehensive DIA window comparison (window-by-window)
  - Handles complex objects (dia_windows DataFrames)
  - Returns single unified DataFrame with Type column

**Keep using find_differences() when you need:**
- Tolerance-based float comparisons
- Comprehensive DIA analysis
- Complete difference report with types

### to_dataframe() for Quick Comparisons

For simpler comparisons without tolerance or complex logic:

```python
# Quick manual comparison
df = collection.to_dataframe(
    method_names=['method1', 'method2'],
    param_names=['Collision_GasSupply_Set', 'dia_window_count']
)

# Find differences manually
for param in df.columns:
    val1 = df.loc['method1', param]
    val2 = df.loc['method2', param]
    if val1 != val2:
        print(f"{param}: {val1} vs {val2}")
```

**DataFrame approach is faster when:**
- You only need simple equality checks (no tolerance)
- You're comparing many parameters at once
- You want to use pandas operations for analysis

**Dict approach (find_differences) is better when:**
- You need tolerance for float comparisons (e.g., `tolerance=1e-6`)
- You need comprehensive DIA comparison
- You want structured output with difference types
- You need to handle complex objects

## Usage Examples

### Example 1: Quick Parameter Check

```python
# Check if collision gas is the same across all methods
df = collection.to_dataframe(param_names=['Collision_GasSupply_Set'])
print(df['Collision_GasSupply_Set'].unique())

# If only one unique value, they're all the same
```

### Example 2: DIA Statistics Comparison

```python
# Compare DIA stats across methods
df = collection.to_dataframe(param_names=[
    'dia_window_count', 'dia_cycle_count',
    'dia_mz_min', 'dia_mz_max'
])

print(df)

# Or use find_differences for comprehensive comparison
diff_df = collection.find_differences(include_params=False)
dia_stats = diff_df[diff_df['Type'] == 'dia_stat']
```

### Example 3: Export for External Analysis

```python
# Get all methods and params as DataFrame
df = collection.to_dataframe()

# Export to Excel
df.to_excel('method_parameters.xlsx')

# Export to CSV
df.to_csv('method_parameters.csv')

# Use in external analysis tools (R, Julia, etc.)
```

### Example 4: Statistical Analysis

```python
import pandas as pd
import numpy as np

# Get numeric parameters across all methods
df = collection.to_dataframe()

# Calculate statistics
numeric_cols = df.select_dtypes(include=[np.number]).columns
stats = df[numeric_cols].describe()
print(stats)

# Find parameters with high variance
variance = df[numeric_cols].var()
high_variance = variance[variance > 0.1].sort_values(ascending=False)
```

### Example 5: Filtering and Subsetting

```python
# Get all methods, filter to specific parameters
df = collection.to_dataframe()

# Filter to TOF-related parameters
tof_params = [col for col in df.columns if 'TOF' in col]
df_tof = df[tof_params]

# Filter to specific methods
methods_of_interest = ['DIA007.proteoscape', 'DIA016.proteoscape']
df_subset = df.loc[methods_of_interest]

# Both filters at once
df_final = df.loc[methods_of_interest, tof_params]
```

## Performance Notes

### Memory Usage

**Dict approach:**
- Lower memory: Only loads one method at a time
- Good for large collections

**DataFrame approach:**
- Higher memory: Loads all methods into single DataFrame
- For 46 methods × 435 params = ~20,000 values (manageable)
- For 1000+ methods, consider subsetting

### Speed

**For single method access:**
- Dict: **Faster** (direct key lookup)
- DataFrame: Slower (needs to build entire DataFrame first)

**For multi-method comparison:**
- Dict: Moderate (iterates through each method)
- DataFrame: **Faster** (vectorized pandas operations)

### Best Practice

For most analyses, use a hybrid approach:

```python
# 1. Use to_dataframe() for overview and filtering
df = collection.to_dataframe()

# 2. Identify methods/parameters of interest
interesting_methods = df[df['dia_window_count'] > 20].index

# 3. Use find_differences() for detailed comparison
diff_df = collection.find_differences(
    method_names=list(interesting_methods),
    include_dia=True
)

# 4. Use dict access for accessing complex objects
for method_name in interesting_methods:
    method = collection[method_name]
    windows = method['dia_windows']
    # Work with the actual DIA windows DataFrame
    print(f"{method_name}: {len(windows)} windows")
```

## Summary

| Feature | Dict Access | DataFrame Access | find_differences() |
|---------|------------|------------------|-------------------|
| Single method | ✓✓✓ Fast | ✗ Slow | N/A |
| Multiple methods | ✓ Good | ✓✓ Better | ✓✓✓ Best for comparison |
| Complex objects | ✓✓✓ Yes | ✓ Limited | ✓✓ Handled |
| Float tolerance | ✗ Manual | ✗ Manual | ✓✓✓ Built-in |
| Export CSV | ✗ No | ✓✓✓ Easy | ✓✓ Possible |
| DIA comparison | ✗ Manual | ✓ Basic | ✓✓✓ Comprehensive |
| Statistical analysis | ✗ Manual | ✓✓✓ Easy | ✓ Moderate |

**Recommendation:**
- **Quick checks & exports**: Use `to_dataframe()`
- **Detailed comparison**: Use `find_differences()`
- **Single method**: Use dict access `collection['name']`
- **Complex workflows**: Combine all three!
