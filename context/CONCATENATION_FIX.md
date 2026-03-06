# Concatenation NaN Bug Fix

## Summary

Fixed critical bugs where concatenating AnnData objects caused data corruption and reindexing errors:

1. **Wrong concatenation axis**: Using axis=0 (rows) instead of axis=1 (columns) → NaN values
2. **Wrong metadata location**: Sample info stored in obs instead of var → lost metadata
3. **Manual index uniquification**: Manual string concatenation → InvalidIndexError
4. **label/keys parameters**: Used with axis=1 → additional reindexing issues

All issues are now fixed with proper axis=1 concatenation, correct metadata placement, and anndata's built-in methods.

## Problem

When adding samples to an existing collection, the data would be corrupted:

**Before Fix:**
```python
# After loading 2 samples:
Shape: (14544, 2)      # Wrong: doubled rows instead of adding columns
Var shape: (2, 0)      # Wrong: lost all var columns
X non-NaN: 50%         # Wrong: half the data is NaN
```

## Root Causes

### Issue 1: Wrong Concatenation Axis

The code was using `ad.concat()` with default axis=0, which:
- Stacks observations (rows) vertically
- Tries to match var (columns) between datasets
- Creates NaN when var don't match (different File.Name for each sample)

```python
# WRONG (axis=0 default)
combined = ad.concat([existing, new_adata], join='outer')
# Result: (14544 rows, 2 cols) but var columns lost, 50% NaN
```

### Issue 2: Sample Metadata in Wrong Location

Sample information was stored in `obs` (observation-level metadata):
```python
adata.obs['Sample'] = sample_name  # WRONG!
```

But with pivoted structure (genes × samples):
- obs (rows) = genes/proteins/precursors
- var (columns) = samples (File.Name)
- Sample is sample-level metadata → should be in var, not obs!

## Solutions

### Fix 1: Use Axis=1 Concatenation

Changed to concatenate along var (columns/samples) axis:

```python
# CORRECT (axis=1)
combined = ad.concat(
    [existing, new_adata],
    axis=1,              # Add samples as new columns
    join='outer',        # Union of genes from both samples
    merge='first'        # Keep first value for non-aligned obs metadata
)
```

**Note:** Removed `label` and `keys` parameters which were causing reindexing errors during axis=1 concatenation.

**Files Modified:** [diann_collection.py](../code/diann_collection.py)
- Lines 273-280: add_from_folder concatenation when appending to existing data
- Lines 285-292: add_from_folder concatenation when creating new combined data
- Lines 431-440: add_single_search concatenation

### Fix 2: Move Sample to Var

Moved Sample from obs to var where it belongs:

```python
# CORRECT
adata.var['UUID'] = sample_name  # Sample-level metadata in var
```

**Files Modified:** [diann_collection.py](../code/diann_collection.py)
- Lines 245, 247: add_from_folder sample metadata
- Lines 401, 403: add_single_search sample metadata

### Fix 3: Use anndata's obs_names_make_unique()

Changed from manual string concatenation to anndata's built-in method for making obs names unique:

```python
# BEFORE (manual string concatenation)
if temp_obs_name.nunique() != adata.n_obs:
    adata.obs[f'{obs_name}_original'] = temp_obs_name
    temp_obs_name = temp_obs_name.astype(str) + '_' + pd.Series(range(len(temp_obs_name))).astype(str)
adata.obs_names = temp_obs_name

# AFTER (using anndata method)
adata.obs_names = temp_obs_name

if not adata.obs_names.is_unique:
    adata.obs[f'{obs_name}_original'] = temp_obs_name.values
    adata.obs_names_make_unique()  # Built-in method handles reindexing correctly
```

**Why:** Manual string concatenation created index values that weren't properly handled by `ad.concat()` during reindexing, causing `InvalidIndexError: Reindexing only valid with uniquely valued Index objects`. The anndata method creates unique indices that are compatible with concat operations.

**Files Modified:** [anndiannloader.py](../code/anndiannloader.py)
- Lines 441-458: Use obs_names_make_unique() instead of manual concatenation

### Fix 4: Update Methods Using Sample

Updated all methods that reference Sample to use var instead of obs:

**get() method** (lines 471-482):
```python
# Filter by sample (select columns)
mask = adata.var['UUID'] == sample
return adata[:, mask].copy()  # Select columns, not rows
```

**list_samples() method** (lines 498-508):
```python
return sorted(self.data[level].var['UUID'].unique().tolist())
```

**to_dataframe() method** (lines 544-558):
```python
# Filter to specific samples (select columns)
mask = adata.var['UUID'].isin(samples)
adata = adata[:, mask].copy()
```

**summary_df() method** (lines 567-581):
```python
samples = adata.var['UUID'].unique()
```

### Fix 5: Remove label/keys Parameters

Removed `label` and `keys` parameters from `ad.concat()` calls which were causing reindexing errors:

```python
# BEFORE (caused reindexing errors)
combined = ad.concat(
    [existing, new_adata],
    axis=1,
    join='outer',
    label='batch',  # ← Problematic for axis=1
    keys=[f'batch_{i}' for i in range(2)],  # ← Problematic for axis=1
    merge='first'
)

# AFTER (fixed)
combined = ad.concat(
    [existing, new_adata],
    axis=1,
    join='outer',
    merge='first'  # No label/keys needed for axis=1
)
```

**Why:** The `label` and `keys` parameters are designed for axis=0 concatenation to track batch information. For axis=1 concatenation (adding samples as columns), they interfere with obs index alignment and cause reindexing errors.

## Results

**After All Fixes:**
```python
# After loading 2 samples:
Shape: (7914, 2)              # Correct: unique genes across 2 samples
Var shape: (2, 3)             # Correct: 2 samples with all metadata
Var columns: ['File.Name', 'UUID', 'search_type']  # Preserved!
X non-NaN: 92%                # Correct: only NaN for genes not in both samples
Layers non-NaN: 92%           # Correct: matching X
Obs index unique: True        # Correct: no duplicates
Reindexing errors: None       # Fixed!
```

**Bulk Loading (19 samples):**
```python
Shape: (9904, 19)             # 9904 unique genes across 19 samples
Var shape: (19, 3)            # 19 samples with metadata
X non-NaN: 47.5%              # Expected: many genes don't appear in all samples
Obs index unique: True        # No reindexing errors
```

### Data Structure

**Correct Structure:**
```
obs (rows):    Genes/Proteins/Precursors (7914 genes)
var (columns): Samples (2 samples)
X:             Quantification matrix (7914 × 2)
Layers:        Additional quantification matrices (same shape as X)

obs columns:   'Genes' (gene names)
var columns:   'File.Name', 'UUID', 'search_type', 'batch'
```

## Test Results

### Before Fix
```
After concatenation:
  Shape: (14544, 2)           # Wrong: doubled rows
  Var columns: []             # Wrong: lost all metadata
  X non-NaN: 14544 / 29088    # Wrong: 50% NaN
```

### After Fix
```
After concatenation:
  Shape: (7914, 2)                    # Correct: unique genes
  Var columns: ['File.Name', 'UUID', 'search_type', 'batch']  # Preserved
  X non-NaN: 14544 / 15828            # Correct: 92% non-NaN
  Layers non-NaN: 14544 / 15828       # Correct: matching X
  Var Sample values: ['search_1', 'search_2']  # Correct
```

## Expected NaN Values

The 8% NaN values are **expected and correct**:
- Total cells: 7914 genes × 2 samples = 15,828 cells
- Non-NaN: 14,544 cells (92%)
- NaN: 1,284 cells (8%)

**Why NaN exists:**
- Sample 1 has 7,255 genes
- Sample 2 has 7,289 genes
- Union: 7,914 unique genes

Some genes only appear in one sample:
- Genes only in sample 1 → NaN in sample 2 column
- Genes only in sample 2 → NaN in sample 1 column

This is the correct behavior for `join='outer'` concatenation.

## Test Files Updated

All test files updated to use `var['UUID']` instead of `obs['Sample']`:
- [test_single_addition_bug.py](../code/tests/test_single_addition_bug.py)
- [test_single_search.py](../code/tests/test_single_search.py)
- [test_single_file_loading.py](../code/tests/test_single_file_loading.py)
- [test_bps_loading.py](../code/tests/test_bps_loading.py)

## Migration

**No user code changes needed** if using the collection API:
```python
# These methods already updated internally
collection.list_samples()           # Uses var['UUID']
collection.get(level, sample='s1')  # Filters by var['UUID']
```

**If directly accessing AnnData objects:**
```python
# OLD (won't work)
samples = adata.obs['Sample'].unique()

# NEW (correct)
samples = adata.var['UUID'].unique()
```

## Key Improvements

1. **Data Integrity**: X and layers preserve all non-missing values (92% vs 50%)
2. **Metadata Preserved**: var columns maintained during concatenation
3. **Correct Structure**: Sample info in var (sample-level) not obs (gene-level)
4. **Proper Filtering**: Methods filter by columns (samples) not rows (genes)
5. **Expected NaN**: Only NaN for genes not present in all samples (outer join)

## Related Issues

These fixes resolve:
- Empty layers after concatenation
- Lost search_type and Sample metadata
- Inability to filter by sample after concatenation
- Wrong sample counts in summary methods
- `InvalidIndexError: Reindexing only valid with uniquely valued Index objects`
- Reindexing errors during axis=1 concatenation

## Files Modified

1. **code/diann_collection.py**
   - Lines 244-248: Move Sample to var in add_from_folder
   - Lines 273-280: Add axis=1 to concatenation in add_from_folder (append)
   - Lines 285-292: Add axis=1 to concatenation in add_from_folder (new)
   - Lines 400-404: Move Sample to var in add_single_search
   - Lines 431-440: Add axis=1 to concatenation in add_single_search
   - Lines 471-482: Update get() to use var['UUID']
   - Lines 498-508: Update list_samples() to use var['UUID']
   - Lines 544-558: Update to_dataframe() to use var['UUID']
   - Lines 567-581: Update summary_df() to use var['UUID']

2. **code/anndiannloader.py**
   - Lines 441-458: Use obs_names_make_unique() instead of manual string concatenation

3. **code/tests/** (all test files updated to use var['UUID'])
