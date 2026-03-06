# Single Search Loading in DiannCollection

## Overview

The `DiannCollection` now supports loading individual search folders, in addition to loading from batch folders and zip archives. This is useful for:
- Adding individual samples one at a time
- Loading samples from different locations
- Building a collection incrementally
- Testing with single search folders

## Usage

### Basic Example

```python
from diann_collection import DiannCollection

with DiannCollection() as collection:
    # Load first search folder
    collection.add_single_search(
        "path/to/search_folder1",
        sample_name="sample1",
        search_type='bps'
    )

    # Load second search folder
    collection.add_single_search(
        "path/to/search_folder2",
        sample_name="sample2",
        search_type='bps'
    )

    # Access combined data
    gene_data = collection['gene']
    print(f"Shape: {gene_data.shape}")
    print(f"Samples: {collection.list_samples('gene')}")
```

### Auto-Detect Sample Name

If you don't provide a sample name, it uses the folder name:

```python
# Folder: /path/to/experiment_A_search/
# Sample name will be: "experiment_A_search"

collection.add_single_search("path/to/experiment_A_search", search_type='bps')
```

### Load Specific Levels

```python
# Load only gene and protein levels
collection.add_single_search(
    "path/to/search_folder",
    sample_name="sample1",
    levels=['gene', 'protein'],
    search_type='bps'
)
```

### Mix with Other Loading Methods

You can combine single search loading with batch folder/zip loading:

```python
with DiannCollection() as collection:
    # Load bulk samples from zip
    collection.add_from_zip("batch_searches.zip", search_type='bps')

    # Add an additional single search
    collection.add_single_search(
        "extra_sample/search_folder",
        sample_name="extra_sample",
        search_type='bps'
    )

    # All samples are now in the collection
    print(f"Total samples: {len(collection.list_samples())}")
```

## Method Signature

```python
def add_single_search(
    self,
    search_path: str,
    sample_name: Optional[str] = None,
    levels: Optional[List[str]] = None,
    sections: Optional[List[str]] = None,
    strict: bool = False,
    search_type: str = 'bps'
)
```

### Parameters

- **search_path** (str): Path to the search folder containing tims-diann.result.zip (BPS) or diann-output folder (FragPipe)
- **sample_name** (str, optional): Name for this sample. If None, uses folder name
- **levels** (List[str], optional): Specific levels to load (precursor, protein, gene). If None, loads all available
- **sections** (List[str], optional): Specific sections to include (var, obs, layers)
- **strict** (bool): If True, raise error if expected columns are missing. Default: False
- **search_type** (str): Type of search folder ('bps' or 'fragpipe'). Default: 'bps'

### Returns

None (modifies the collection in-place)

## Features

### 1. Automatic Concatenation

When you add multiple search folders, they're automatically concatenated:

```python
collection.add_single_search("search_folder1", sample_name="s1", search_type='bps')
collection.add_single_search("search_folder2", sample_name="s2", search_type='bps')

# Result: (genes_from_s1 + genes_from_s2, 2 samples)
print(collection['gene'].shape)  # e.g., (14544, 2)
```

### 2. Smart Column Selection

Uses the same smart column selection as folder loading:
- Automatically selects best available columns
- Tries alternative quantification columns if first fails
- Aggregates duplicates for gene level

### 3. Progress Display

Shows detailed loading progress:

```
Loading single search from: /path/to/search_folder
  Search type: bps
  Sample name: sample_1

Processing sample_1...
  Searching for tims-diann.result.zip files...
  Found 1 result file
  Loading gene level...
Loaded 79257 rows with 8/8 columns for level 'gene'
Using 'Genes' as obs_name (non-unique, will be made unique)
Using 'File.Name' as var_name
  Aggregating duplicate 'Genes' values using max()
Using 'Genes.MaxLFQ' as x (quantification column)
    ✓ gene: (7255, 1)

AnnData object with n_obs × n_vars = 7255 × 1
    obs: 'Genes', 'Sample'
    var: 'File.Name', 'search_type'
    layers: 'Genes.MaxLFQ', 'Genes.Quantity', 'Genes.Normalised', ...
```

## Examples

### Example 1: Sequential Loading

```python
# Load search folders one by one as they become available
with DiannCollection() as collection:
    for i, search_folder in enumerate(search_folders):
        collection.add_single_search(
            search_folder,
            sample_name=f"sample_{i+1}",
            search_type='bps'
        )

    # Save after each addition if needed
    collection.save("collection.pkl")
```

### Example 2: Mixed Sources

```python
# Combine samples from different locations
with DiannCollection() as collection:
    # Load batch from BPS format
    collection.add_from_zip("bps_searches.zip", search_type='bps')

    # Add individual BPS samples
    collection.add_single_search("bps_sample1_folder", sample_name="bps1", search_type='bps')
    collection.add_single_search("bps_sample2_folder", sample_name="bps2", search_type='bps')

    # Add individual FragPipe samples
    collection.add_single_search("fragpipe_sample1", sample_name="fp1", search_type='fragpipe')
    collection.add_single_search("fragpipe_sample2", sample_name="fp2", search_type='fragpipe')

    print(f"Total samples: {len(collection.list_samples())}")
```

### Example 3: Incremental Building

```python
# Build collection incrementally over time
collection = DiannCollection()

# Week 1: Add first batch
collection.add_single_search("week1_search1", sample_name="w1_s1", search_type='bps')
collection.add_single_search("week1_search2", sample_name="w1_s2", search_type='bps')
collection.save("week1_collection.pkl")

# Week 2: Load and add more
collection = DiannCollection.from_file("week1_collection.pkl")
collection.add_single_search("week2_search1", sample_name="w2_s1", search_type='bps')
collection.add_single_search("week2_search2", sample_name="w2_s2", search_type='bps')
collection.save("week2_collection.pkl")
```

## Comparison with Other Methods

| Method | Use Case | Input |
|--------|----------|-------|
| `add_single_search()` | Single search folder | Folder containing tims-diann.result.zip or diann-output |
| `add_from_folder()` | Folder with multiple samples | Directory or zip with multiple searches |
| `add_from_zip()` | Alias for add_from_folder | Zip archive with multiple searches |

All methods:
- Use the same loading logic
- Support smart column selection
- Automatically concatenate samples
- Display AnnData summaries

## Error Handling

### Folder Not Found

```python
try:
    collection.add_single_search("nonexistent_folder", search_type='bps')
except FileNotFoundError as e:
    print(f"Error: {e}")
```

### No Results Files Found

```python
try:
    collection.add_single_search("empty_folder", search_type='bps')
except FileNotFoundError as e:
    print(f"Error: No results files found")
```

### Missing Columns

With `strict=False` (default), shows warnings but continues:

```python
collection.add_single_search("search_folder", strict=False, search_type='bps')
# Output: ⚠ Note: gene level missing some columns: ...
```

With `strict=True`, raises error:

```python
collection.add_single_search("search_folder", strict=True, search_type='bps')
# Raises KeyError if required columns missing
```

## Implementation Details

The method:
1. Validates the search path exists
2. Uses `_find_results_files()` to recursively search for tims-diann.result.zip (BPS) or diann-output folders (FragPipe)
3. Determines sample name (from parameter or folder name)
4. Extracts nested zips if needed
5. Checks available columns (header-only read)
6. Loads each requested level
7. Adds Sample and search_type metadata
8. Concatenates with existing data (if any)

Code location: [diann_collection.py:296-421](../code/diann_collection.py#L296-L421)

## Benefits

1. **Flexibility**: Mix and match search folders from different sources and formats (BPS/FragPipe)
2. **Incremental**: Build collections over time
3. **Testing**: Easy to test with individual search folders
4. **Control**: Fine-grained control over which searches to include
5. **Transparency**: See exactly what's being loaded with detailed progress display
6. **Robustness**: Same robust search logic as batch loading (handles nested zips, multiple naming patterns)

## Migration

No changes needed to existing code. This is a new feature that complements existing loading methods.
