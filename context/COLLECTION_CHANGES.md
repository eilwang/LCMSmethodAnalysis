# DiannCollection Changes Summary

## Major Structural Changes

### 1. New Collection Data Structure

**OLD Structure:**
```python
collection.data = {
    'sample1': {
        'precursor': AnnData,
        'protein': AnnData,
        'gene': AnnData
    },
    'sample2': {
        'precursor': AnnData,
        'protein': AnnData
    }
}
```

**NEW Structure:**
```python
collection.data = {
    'precursor': AnnData,  # Contains ALL samples concatenated
    'protein': AnnData,    # Contains ALL samples concatenated
    'gene': AnnData        # Contains ALL samples concatenated
}
```

**Key Benefits:**
- Simpler access: `collection['precursor']` gives you all samples at once
- Easier analysis: All samples already combined for multi-sample comparisons
- More memory efficient: Single concatenated object per level
- Each AnnData has `Sample` column in `obs` to identify samples

### 2. Search Type Support

Added `search_type` parameter to handle different DIA-NN output formats:

**BPS Format (default):**
```
searches/
├── sample1-tims-diann.result.zip
│   └── result.tsv         # ← Looks for result.tsv
├── sample2-tims-diann.result.zip
│   └── result.tsv
```

**FragPipe Format:**
```
searches/
├── sample1/
│   └── diann-output/
│       └── report.tsv    # ← Looks for diann-output/report.tsv
├── sample2/
│   └── diann-output/
│       └── report.tsv
```

**Usage:**
```python
# BPS format (default)
collection.add_from_folder("searches/", search_type='bps')

# FragPipe format
collection.add_from_folder("searches/", search_type='fragpipe')
```

**Metadata:**
The `search_type` is automatically added to `adata.var['search_type']` so you can track which format each sample came from.

### 3. Efficient Column Checking

The collection now:
1. Reads only the header line first (fast!)
2. Checks which columns are present
3. Shows informative warnings about missing columns
4. Attempts to load data with available columns

## Understanding KeyErrors

### Why Do They Happen?

KeyErrors occur when **essential pivot columns** are missing. To create an AnnData object, we need:

1. **var_name**: Column to use as variable (column) names (e.g., `File.Name`)
2. **obs_name**: Column to use as observation (row) names (e.g., `Precursor.Id`, `Genes`)
3. **x**: Column with the main quantification values (e.g., `Precursor.Quantity`, `Genes.MaxLFQ`)

**Example:**
```
For gene level:
- var_name: File.Name
- obs_name: Genes
- x: Genes.MaxLFQ   ← If this is missing, pivot fails with KeyError
```

### What Columns Can Be Missing?

**Can be missing (will load with warnings):**
- Layers columns (RT, IM, Q.Value, etc.)
- Optional metadata columns

**Cannot be missing (will cause KeyError):**
- The var_name column (File.Name)
- The obs_name column (Precursor.Id, Protein.Ids, Genes)
- The x column (Precursor.Quantity, PG.MaxLFQ, Genes.MaxLFQ)
- Essential obs columns needed for the index

### How to Fix KeyErrors

**Option 1: Check which columns are actually required**
```python
from anndiannloader import DiannLoader

loader = DiannLoader()
available = loader.check_available_levels("path/to/result.tsv")

for level, info in available.items():
    if not info['available']:
        print(f"{level}: missing {info['missing_columns']}")
```

**Option 2: Only load levels that have all required columns**
```python
collection.add_from_folder(
    "searches/",
    levels=['precursor'],  # Only load precursor if gene/protein columns missing
    search_type='bps'
)
```

**Option 3: Update your DIA-NN output**
Make sure your DIA-NN search includes the required columns. For example, if you want gene-level data, ensure your search outputs `Genes.MaxLFQ`.

## New API Examples

### Basic Usage
```python
from diann_collection import DiannCollection

# Create collection and load BPS format data
with DiannCollection() as collection:
    collection.add_from_folder("searches.zip", search_type='bps')

    # Access combined data for a level
    precursor_data = collection['precursor']
    print(f"Shape: {precursor_data.shape}")
    print(f"Samples: {precursor_data.obs['Sample'].unique()}")

    # Get data for specific sample
    sample1_precursor = collection.get('precursor', sample='sample1')

    # List what's available
    print(f"Levels: {collection.list_levels()}")
    print(f"Samples: {collection.list_samples()}")
    print(f"Samples in precursor: {collection.list_samples('precursor')}")
```

### Access Patterns

**Old way (no longer works):**
```python
# collection['sample1', 'precursor']  # ❌ No longer valid
```

**New way:**
```python
# Get all samples for a level
all_precursor = collection['precursor']  # ✓ Returns combined AnnData

# Get specific sample for a level
sample1_precursor = collection.get('precursor', sample='sample1')  # ✓

# Get all samples for a level (explicit)
all_precursor = collection.get('precursor')  # ✓
```

### Working with Samples

```python
# Get all samples across all levels
all_samples = collection.list_samples()

# Get samples for specific level
precursor_samples = collection.list_samples('precursor')

# Filter to specific samples
precursor_data = collection['precursor']
sample_mask = precursor_data.obs['Sample'].isin(['sample1', 'sample2'])
filtered = precursor_data[sample_mask]
```

## Migration from Old Structure

If you have code using the old structure:

**OLD:**
```python
adata = collection['sample1', 'precursor']
```

**NEW:**
```python
adata = collection.get('precursor', sample='sample1')
# or
all_data = collection['precursor']
adata = all_data[all_data.obs['Sample'] == 'sample1']
```

## Summary of Method Changes

| Method | OLD Behavior | NEW Behavior |
|--------|-------------|--------------|
| `__getitem__` | `collection['sample', 'level']` | `collection['level']` returns combined AnnData |
| `get()` | `get(sample, level)` | `get(level, sample=None)` - level first, optional sample filter |
| `list_samples()` | Returns list of sample names | Same, but can filter by level |
| `list_levels()` | `list_levels(sample)` per-sample | `list_levels()` returns all levels in collection |
| `add_from_folder()` | No search_type | Added `search_type='bps'` parameter |
| `add_from_zip()` | No search_type | Added `search_type='bps'` parameter |
