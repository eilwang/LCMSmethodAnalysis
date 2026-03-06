# Smart Column Selection in DiannLoader

## Overview

The DiannLoader now automatically selects the best available columns for creating AnnData objects, instead of failing if specific columns are missing. This makes it more robust for handling different DIA-NN output formats.

## How It Works

### 1. Observation Names (obs_name)

Selects from the `obs` section of the config:

**Priority:**
1. First obs column that exists AND has all unique values
2. If no unique column found, uses first available obs column (will be made unique automatically)

**Example:**
```
Config obs section: [Protein.Group, Protein.Ids, Protein.Names, Genes, ...]
Available in file: [Protein.Group, Genes, Modified.Sequence]

Selection: Protein.Group (unique values) ✓
```

### 2. Variable Names (var_name)

Selects from the `var` section of the config:

**Priority:**
1. First var column that exists

**Example:**
```
Config var section: [File.Name, Run]
Available in file: [File.Name, Run]

Selection: File.Name ✓
```

### 3. Quantification Column (x)

Selects from the `layers` section of the config:

**Priority:**
1. First layer column that exists AND is not all empty/zero

**Example:**
```
Config layers section: [Precursor.Quantity, Precursor.Normalised, IM, ...]
Available in file: [Precursor.Quantity, Precursor.Normalised]

Check: Precursor.Quantity has values (1000, 2000, 1500) ✓
Selection: Precursor.Quantity
```

## Benefits

### 1. Handles Missing Columns Gracefully

**Before:**
```
KeyError: 'Precursor.Charge' is required but missing
```

**After:**
```
Using 'Protein.Group' as obs_name (unique values)
Using 'File.Name' as var_name
Using 'Precursor.Quantity' as x (quantification column)
✓ Successfully created AnnData: (3, 1)
```

### 2. Adapts to Different Output Formats

Works with TIMS-DIA-NN files that may have different column sets than standard DIA-NN.

### 3. Informative Messages

Prints which columns are selected so you know what's being used:
```
Using 'Precursor.Id' as obs_name (unique values)
Using 'File.Name' as var_name
Using 'Precursor.Quantity' as x (quantification column)
```

## BPS Folder Improvements

The collection now searches through subfolders for BPS format:

**Before:**
```
FileNotFoundError: No results files found
```

**After:**
Recursively searches all subfolders for:
- `*.result.zip` files
- Any zip containing 'tims-diann' in the name
- `result.tsv` files directly

**Structure handled:**
```
project/
├── sample1/
│   └── xxx-tims-diann.result.zip  ← Found!
│       └── result.tsv
├── sample2/
│   └── yyy-tims-diann.result.zip  ← Found!
│       └── result.tsv
```

## Configuration

No changes needed to `diann_columns.yaml`! The existing structure works:

```yaml
levels:
  precursor:
    var:
      - File.Name  # Will try this first
      - Run        # Then this
    obs:
      - Protein.Group      # Will try this first (if unique)
      - Protein.Ids        # Then this
      - Modified.Sequence  # Then this
      # ...
    layers:
      - Precursor.Quantity   # Will try this first (if not empty)
      - Precursor.Normalised # Then this
      # ...
```

## Error Handling

### Clear Error Messages

If NO valid columns found:
```
KeyError: Cannot create AnnData for level 'precursor':
no valid obs column found. Tried: [Protein.Group, Protein.Ids, ...]
```

### Automatic Uniqueness

If obs_name column is not unique:
```
Using 'Modified.Sequence' as obs_name (non-unique, will be made unique)
<appends indices to make unique>
```

## Examples

### Example 1: Full Column Set
```python
# File has all columns
loader.load_to_adata("full_results.tsv", level="precursor")

# Output:
# Using 'Precursor.Id' as obs_name (unique values)
# Using 'File.Name' as var_name
# Using 'Precursor.Quantity' as x
```

### Example 2: Minimal Column Set
```python
# File missing many columns
loader.load_to_adata("minimal_results.tsv", level="precursor")

# Output:
# Using 'Protein.Group' as obs_name (unique values)
# Using 'Run' as var_name
# Using 'Precursor.Normalised' as x (Quantity missing)
```

### Example 3: Gene Level with Missing Columns
```python
# Gene level file missing Genes.MaxLFQ
loader.load_to_adata("results.tsv", level="gene")

# Output:
# Using 'Genes' as obs_name (unique values)
# Using 'File.Name' as var_name
# Using 'Genes.Quantity' as x (MaxLFQ missing but Quantity available)
```

## Technical Details

### Selection Logic

```python
# For obs_name
for candidate in config['obs']:
    if candidate in df.columns:
        if df[candidate].nunique() == len(df):
            obs_name = candidate  # Use this!
            break

# For var_name
for candidate in config['var']:
    if candidate in df.columns:
        var_name = candidate  # Use this!
        break

# For x
for candidate in config['layers']:
    if candidate in df.columns:
        if not df[candidate].isna().all() and (df[candidate] != 0).any():
            x_col = candidate  # Use this!
            break
```

### Pivot Construction

Only uses obs columns that actually exist:
```python
available_obs_cols = [col for col in config['obs'] if col in df.columns]
pivot_df = df.pivot(index=available_obs_cols, columns=var_name, values=x_col)
```

### Automatic Aggregation for Non-Unique Observations

When observation names have duplicates (common for gene level where multiple precursors map to one gene), the loader automatically:

1. **Detects duplicates**: Checks if `obs_name` has duplicate values
2. **Aggregates all numeric columns**: Uses `max()` aggregation for all numeric columns
3. **Preserves all layers**: All data columns are aggregated, not just the main quantification column

```python
# Detects duplicates
needs_aggregation = df[obs_name].duplicated().any()

if needs_aggregation:
    # Aggregate ALL numeric columns using max()
    numeric_cols = df.select_dtypes(include=['number']).columns
    cols_to_aggregate = [col for col in numeric_cols if col not in groupby_cols]

    agg_dict = {col: 'max' for col in cols_to_aggregate}
    df_for_pivot = df.groupby(groupby_cols, as_index=False).agg(agg_dict)
```

**Example:**
```
Gene level with 79,257 precursors → 7,255 unique genes
- Automatically aggregates duplicate gene entries
- All layers preserved with max() values
- Result: Clean gene-level matrix with all quantification data
```

## Migration

No code changes needed! Existing code will automatically benefit from:
- More robust loading
- Better error messages
- Support for files with missing columns

```python
# This works the same as before, but now handles missing columns
loader = DiannLoader()
adata = loader.load_to_adata("results.tsv", level="precursor", strict=False)
```
