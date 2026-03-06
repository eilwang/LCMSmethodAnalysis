# DIA-NN Collection Loader

A Python tool for loading and merging multiple DIA-NN search results from zip archives.

## Features

- **Automatic extraction**: Handles nested zip structures (e.g., `tims-diann.result.zip` files within a main archive)
- **Flexible merging**: Supports multiple merge strategies (concat, outer, inner)
- **Multi-level analysis**: Load data at precursor, protein, or gene levels
- **AnnData support**: Create AnnData objects for single-cell style analysis
- **Automatic cleanup**: Temporary files are automatically cleaned up

## Installation

Requires:
- pandas
- anndata
- pyyaml
- numpy

```bash
pip install pandas anndata pyyaml numpy
```

## Quick Start

### Basic Usage

```python
from diann_collection_loader import DiannCollectionLoader

# Load from a zip file
with DiannCollectionLoader() as loader:
    df = loader.load_from_zip(
        "diann_searches.zip",
        level="precursor",
        merge_method='concat'
    )

    print(f"Loaded {len(df)} precursors from {df['Sample'].nunique()} samples")

# Or load from a folder (more flexible - accepts folder or zip)
with DiannCollectionLoader() as loader:
    df = loader.load_from_folder(
        "diann_searches",  # Can be a folder or zip file
        level="precursor",
        merge_method='concat'
    )

    print(f"Loaded {len(df)} precursors from {df['Sample'].nunique()} samples")
```

### Expected Zip Structure

The loader handles two common structures:

**Option 1: Nested zip files**
```
diann_searches.zip/
├── sample1-tims-diann.result.zip
│   └── results.tsv
├── sample2-tims-diann.result.zip
│   └── results.tsv
└── sample3-tims-diann.result.zip
    └── results.tsv
```

**Option 2: Flattened structure**
```
diann_searches.zip/
├── sample1/
│   └── results.tsv
├── sample2/
│   └── results.tsv
└── sample3/
    └── results.tsv
```

## Usage Examples

### 1. Load from Folder or Zip (Flexible)

```python
with DiannCollectionLoader() as loader:
    # Works with folders
    df_folder = loader.load_from_folder(
        "path/to/searches_folder",
        level="precursor",
        merge_method='concat'
    )

    # Also works with zip files
    df_zip = loader.load_from_folder(
        "path/to/searches.zip",
        level="precursor",
        merge_method='concat'
    )

    # Both produce the same result
    print(f"Loaded {len(df_folder)} rows")
```

### 2. Load at Different Levels

```python
with DiannCollectionLoader() as loader:
    # Precursor level (most detailed)
    df_precursor = loader.load_from_folder(
        "diann_searches.zip",
        level="precursor",
        merge_method='concat'
    )

    # Protein level (aggregated from peptides)
    df_protein = loader.load_from_folder(
        "diann_searches.zip",
        level="protein",
        merge_method='concat'
    )
```

### 3. Different Merge Methods

```python
with DiannCollectionLoader() as loader:
    # Concat: Long format with all samples (recommended)
    df_long = loader.load_from_folder(
        "diann_searches.zip",
        level="precursor",
        merge_method='concat'
    )

    # Outer: Wide format, keeps all features from all samples
    df_wide = loader.load_from_folder(
        "diann_searches.zip",
        level="precursor",
        merge_method='outer'
    )

    # Inner: Only features present in all samples
    df_common = loader.load_from_folder(
        "diann_searches.zip",
        level="precursor",
        merge_method='inner'
    )
```

### 4. Create AnnData Objects

```python
with DiannCollectionLoader() as loader:
    # Create merged AnnData object
    adata = loader.load_to_adata_collection(
        "diann_searches.zip",
        level="precursor",
        merge_obs=True  # Merge all samples
    )

    print(f"Shape: {adata.shape}")
    print(f"Samples: {adata.n_obs}")
    print(f"Precursors: {adata.n_vars}")
    print(f"Layers: {list(adata.layers.keys())}")
```

### 5. Load Specific Sections

```python
with DiannCollectionLoader() as loader:
    # Load only essential columns
    df = loader.load_from_folder(
        "diann_searches.zip",
        level="precursor",
        sections=["var", "obs", "x"],  # Only identifiers and quantification
        merge_method='concat'
    )
```

### 6. Multi-Level Analysis

```python
# Manual loading of each level
results = {}

with DiannCollectionLoader() as loader:
    for level in ["precursor", "protein"]:
        results[level] = loader.load_from_folder(
            "diann_searches.zip",
            level=level,
            merge_method='concat'
        )

# Compare levels
for level, df in results.items():
    print(f"{level}: {len(df)} rows, {df['Sample'].nunique()} samples")
```

### 7. Load All Levels at Once

```python
with DiannCollectionLoader() as loader:
    # Load all levels in one call
    all_levels = loader.load_from_folder(
        "diann_searches.zip",
        level=None,  # or level='all'
        merge_method='concat'
    )

    # Returns dictionary with all levels
    print(f"Loaded levels: {list(all_levels.keys())}")

    # Access each level
    df_precursor = all_levels['precursor']
    df_protein = all_levels['protein']
    df_gene = all_levels['gene']

    # Compare
    for level, df in all_levels.items():
        print(f"{level}: {df.shape}")
```

## API Reference

### DiannCollectionLoader

Main class for loading and merging DIA-NN search results.

#### Methods

##### `load_from_zip(zip_path, level, sections=None, strict=False, merge_method='outer')`

Load and merge DIA-NN results from a zip archive.

**Parameters:**
- `zip_path` (str): Path to zip file containing DIA-NN search results
- `level` (str or None): Analysis level - "precursor", "protein", or "gene". If None or "all", loads all levels
- `sections` (List[str], optional): Specific sections to include (var, obs, x, layers, etc.)
- `strict` (bool): If True, raise error if expected columns are missing
- `merge_method` (str): Merge strategy - "outer", "inner", or "concat"

**Returns:**
- `pd.DataFrame` or `Dict[str, pd.DataFrame]`: Merged DataFrame if level specified, or dictionary of DataFrames for all levels if level=None

**Example:**
```python
df = loader.load_from_zip(
    "searches.zip",
    level="precursor",
    merge_method='concat'
)
```

##### `load_from_folder(folder_path, level, sections=None, strict=False, merge_method='outer')`

Load and merge DIA-NN results from a folder or zip file (more flexible version).

**Parameters:**
- `folder_path` (str): Path to folder or zip file containing DIA-NN search results
- `level` (str or None): Analysis level - "precursor", "protein", or "gene". If None or "all", loads all levels
- `sections` (List[str], optional): Specific sections to include (var, obs, x, layers, etc.)
- `strict` (bool): If True, raise error if expected columns are missing
- `merge_method` (str): Merge strategy - "outer", "inner", or "concat"

**Returns:**
- `pd.DataFrame` or `Dict[str, pd.DataFrame]`: Merged DataFrame if level specified, or dictionary of DataFrames for all levels if level=None

**Accepts:**
- Directory containing results.tsv files or nested zips
- Zip file containing results.tsv files or nested zips

**Example:**
```python
# Load from a directory
df = loader.load_from_folder(
    "searches_folder",
    level="precursor",
    merge_method='concat'
)

# Or load from a zip file (same method)
df = loader.load_from_folder(
    "searches.zip",
    level="precursor",
    merge_method='concat'
)
```

##### `load_to_adata_collection(zip_path, level, sections=None, strict=False, merge_obs=True)`

Load DIA-NN results and create merged AnnData object.

**Parameters:**
- `zip_path` (str): Path to zip file
- `level` (str or None): Analysis level. If None or "all", loads all levels
- `sections` (List[str], optional): Specific sections to include
- `strict` (bool): If True, raise error on missing columns
- `merge_obs` (bool): If True, merge all samples into one AnnData

**Returns:**
- `ad.AnnData` or `Dict[str, ad.AnnData]`: Merged AnnData if level specified, or dictionary of AnnData objects for all levels if level=None

**Example:**
```python
adata = loader.load_to_adata_collection(
    "searches.zip",
    level="precursor",
    merge_obs=True
)
```

## Merge Methods

### Concat (Recommended)
- Creates long-format DataFrame
- Concatenates all samples vertically
- Preserves all data
- Best for most analyses

```python
merge_method='concat'
```

### Outer
- Creates wide-format DataFrame
- Includes all features from all samples
- Missing values filled with NaN
- Useful for direct sample comparison

```python
merge_method='outer'
```

### Inner
- Creates wide-format DataFrame
- Only includes features present in ALL samples
- No missing values
- Useful for core set analysis

```python
merge_method='inner'
```

## Configuration

The loader uses `diann_columns.yaml` to define column mappings for each level. Make sure this file is in your working directory or specify the path:

```python
loader = DiannCollectionLoader(config_path="path/to/diann_columns.yaml")
```

## Error Handling

The loader provides informative warnings and errors:

```python
with DiannCollectionLoader() as loader:
    try:
        df = loader.load_from_zip("searches.zip", level="precursor")
    except FileNotFoundError as e:
        print(f"No results files found: {e}")
    except ValueError as e:
        print(f"Invalid configuration: {e}")
```

## Testing

Run the test suite:

```bash
python tests/test_diann_collection.py
```

Run the examples:

```bash
python examples/example_diann_collection.py /path/to/searches.zip
```

## Performance Tips

1. **Use concat method** for most cases - it's fastest and preserves all data
2. **Specify sections** to load only needed columns and reduce memory usage
3. **Use context manager** (`with` statement) to ensure cleanup
4. **Load at appropriate level** - protein level is pre-aggregated and smaller

## Troubleshooting

### "No results.tsv files found"
- Check that your zip contains the expected structure
- Ensure files are named exactly "results.tsv"
- Verify nested zips are valid zip files

### "Missing columns"
- Update your `diann_columns.yaml` to match your DIA-NN version
- Use `strict=False` to continue with available columns

### Memory issues
- Load only specific sections: `sections=["var", "obs", "x"]`
- Load at protein level instead of precursor level
- Process samples in batches

## License

This tool is part of the DIA-NN analysis pipeline.

## Related Files

- `anndiannloader.py`: Base DiannLoader class
- `diann_columns.yaml`: Column configuration file
- `examples/example_diann_collection.py`: Usage examples
- `tests/test_diann_collection.py`: Test suite
