# DIA-NN Collection

A collection object for managing multiple DIA-NN search results, following the same design pattern as `MSMethodCollection` and `LCMethodCollection`.

## Key Features

- **Collection-based storage**: Stores DIA-NN searches as AnnData objects internally
- **Multi-level support**: Automatically loads data at precursor, protein, and gene levels
- **Easy access**: Dictionary-style access to samples and levels
- **Persistence**: Save and load entire collections
- **Summary generation**: Create overview DataFrames of your data

## Design Philosophy

Unlike the previous `DiannCollectionLoader` which returned DataFrames directly, `DiannCollection` is a **collection object** that:

1. Stores searches internally as AnnData objects (organized by sample and level)
2. Provides collection-style access methods (`collection[sample, level]`)
3. Can be saved and loaded as a complete unit
4. Follows the same API pattern as other collection classes in the project

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
from diann_collection import DiannCollection

# Create collection and load data
with DiannCollection() as collection:
    # Load searches from zip file
    collection.add_from_zip("diann_searches.zip")

    # Access data
    print(f"Samples: {collection.list_samples()}")
    print(f"Levels: {collection.list_levels()}")

    # Get specific AnnData object
    adata = collection['sample1', 'precursor']
    print(f"Shape: {adata.shape}")

    # Save collection
    collection.save("my_collection.pkl")

# Load saved collection
collection = DiannCollection.from_file("my_collection.pkl")
```

### Expected Data Structure

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

### 1. Loading Data

```python
from diann_collection import DiannCollection

# Create empty collection
collection = DiannCollection()

# Add data from zip file (loads all levels by default)
collection.add_from_zip("searches.zip")

# Or add from folder
collection.add_from_folder("/path/to/searches/")

# Load specific levels only
collection.add_from_zip("searches.zip", levels=['precursor', 'protein'])

print(f"Loaded {len(collection)} samples")
```

### 2. Accessing Data

```python
# List all samples
samples = collection.list_samples()
print(f"Samples: {samples}")

# List all levels
levels_dict = collection.list_levels()
print(f"Levels: {levels_dict}")

# Get levels for specific sample
sample_levels = collection.list_levels('sample1')
print(f"Sample1 levels: {sample_levels}")

# Access specific AnnData object
adata = collection.get('sample1', 'precursor')
# or
adata = collection['sample1', 'precursor']

# Access all levels for a sample
sample1_data = collection['sample1']  # Returns dict of AnnData objects
precursor_adata = sample1_data['precursor']
protein_adata = sample1_data['protein']

# Check if sample exists
if 'sample1' in collection:
    print("Sample1 is in collection")
```

### 3. Summary and Inspection

```python
# Get summary DataFrame
summary = collection.summary_df()
print(summary)

# Example output:
#      Sample  precursor_n_obs  precursor_n_vars precursor_shape  protein_n_obs  protein_n_vars protein_shape
# 0  sample1              150             5000       (150, 5000)             30            2000     (30, 2000)
# 1  sample2              140             4800       (140, 4800)             28            1900     (28, 1900)

# String representation
print(collection)  # DiannCollection(samples=2, levels=[precursor, protein, gene])

# Collection length
print(f"Number of samples: {len(collection)}")
```

### 4. Saving and Loading

```python
# Save as pickle (recommended for Python)
collection.save("my_collection.pkl")

# Save as h5ad directory structure
collection.save("my_collection.h5ad")

# Load saved collection
loaded = DiannCollection.from_file("my_collection.pkl")

# Or load from h5ad directory
loaded = DiannCollection.from_file("my_collection.h5ad")
```

### 5. Converting to DataFrame

```python
# Convert specific level to merged DataFrame
df_precursor = collection.to_df(level='precursor', merge_method='concat')

# Convert specific samples only
df_subset = collection.to_df(
    level='precursor',
    samples=['sample1', 'sample2'],
    merge_method='concat'
)
```

### 6. Working with AnnData Objects

```python
# Since data is stored as AnnData, you can use all AnnData functionality

adata = collection['sample1', 'precursor']

# Access the data matrix
X = adata.X

# Access observation (run) metadata
obs = adata.obs
print(f"Runs: {obs.index}")
print(f"Sample names: {obs['Sample'].unique()}")

# Access variable (precursor/protein) metadata
var = adata.var
print(f"Features: {var.index}")

# Access layers (different quantification types)
for layer_name in adata.layers.keys():
    print(f"Layer '{layer_name}': {adata.layers[layer_name].shape}")

# Perform AnnData operations
import scanpy as sc
# Example: normalize, log-transform, etc.
```

### 7. Context Manager

```python
# Use context manager for automatic cleanup of temporary files
with DiannCollection() as collection:
    collection.add_from_zip("searches.zip")

    # Work with collection
    adata = collection['sample1', 'precursor']

    # Temporary directories automatically cleaned up on exit
```

## API Reference

### DiannCollection

Main collection class for managing DIA-NN search results.

#### Constructor

```python
DiannCollection(config_path: str = "diann_columns.yaml")
```

**Parameters:**
- `config_path` (str): Path to YAML configuration file defining column mappings

#### Methods

##### `add_from_zip(zip_path, levels=None, sections=None, strict=False)`

Load DIA-NN results from zip archive and add to collection.

**Parameters:**
- `zip_path` (str): Path to zip file
- `levels` (List[str], optional): Specific levels to load. If None, loads all levels
- `sections` (List[str], optional): Specific sections to include
- `strict` (bool): If True, raise error if expected columns are missing

##### `add_from_folder(folder_path, levels=None, sections=None, strict=False)`

Load DIA-NN results from folder and add to collection.

**Parameters:**
- `folder_path` (str): Path to folder or zip file
- `levels` (List[str], optional): Specific levels to load
- `sections` (List[str], optional): Specific sections to include
- `strict` (bool): If True, raise error if expected columns are missing

##### `get(sample_name, level)`

Get AnnData object for specific sample and level.

**Parameters:**
- `sample_name` (str): Name of the sample
- `level` (str): Analysis level (precursor, protein, gene)

**Returns:**
- `ad.AnnData`: AnnData object

##### `list_samples()`

List all sample names in collection.

**Returns:**
- `List[str]`: Sample names

##### `list_levels(sample_name=None)`

List all levels, optionally for a specific sample.

**Parameters:**
- `sample_name` (str, optional): If provided, return levels for this sample only

**Returns:**
- `List[str]` or `Dict[str, List[str]]`: Levels

##### `to_df(level, samples=None, merge_method='concat')`

Convert stored AnnData objects to merged DataFrame.

**Parameters:**
- `level` (str): Analysis level
- `samples` (List[str], optional): Specific samples to include
- `merge_method` (str): How to merge ('concat', 'outer', 'inner')

**Returns:**
- `pd.DataFrame`: Merged DataFrame

##### `summary_df()`

Create summary DataFrame.

**Returns:**
- `pd.DataFrame`: Summary showing all samples and their shapes

##### `save(filepath)`

Save collection to file.

**Parameters:**
- `filepath` (str): Path to save file (.pkl or .h5ad)

##### `from_file(filepath, config_path="diann_columns.yaml")` (classmethod)

Load collection from file.

**Parameters:**
- `filepath` (str): Path to saved file
- `config_path` (str): Path to YAML configuration file

**Returns:**
- `DiannCollection`: Loaded collection

#### Special Methods

```python
# Dictionary-style access
adata = collection['sample1', 'precursor']  # Get specific AnnData
sample_dict = collection['sample1']  # Get all levels for sample

# Membership testing
if 'sample1' in collection:
    print("Sample exists")

# Length
n_samples = len(collection)

# String representation
print(collection)  # DiannCollection(samples=3, levels=[precursor, protein, gene])
```

## Comparison with DiannCollectionLoader

### Old: DiannCollectionLoader
```python
# Returns DataFrames/dictionaries directly
loader = DiannCollectionLoader()
df = loader.load_from_zip("searches.zip", level="precursor")
# No persistence, no collection management
```

### New: DiannCollection
```python
# Collection object with persistence
collection = DiannCollection()
collection.add_from_zip("searches.zip")
adata = collection['sample1', 'precursor']
collection.save("collection.pkl")

# Load later
collection = DiannCollection.from_file("collection.pkl")
```

## Advantages of Collection Approach

1. **Organized storage**: All data for a project in one object
2. **Easy access**: Dictionary-style access to any sample/level
3. **Persistence**: Save and load entire collections
4. **AnnData native**: Full access to AnnData ecosystem (scanpy, etc.)
5. **Consistent API**: Same pattern as MS and LC method collections
6. **Memory efficient**: Only loads data when needed

## Performance Tips

1. **Load specific levels**: If you only need precursor data, specify `levels=['precursor']`
2. **Use pickle format**: `.pkl` files are faster than `.h5ad` directory structures
3. **Context manager**: Use `with` statement for automatic cleanup
4. **Batch operations**: Add multiple zip files before processing

## Troubleshooting

### "No results.tsv files found"
- Check that your zip contains the expected structure
- Ensure files are named exactly "results.tsv"
- Verify nested zips are valid zip files

### "Missing columns"
- Update your `diann_columns.yaml` to match your DIA-NN version
- Use `strict=False` to continue with available columns

### Memory issues
- Load specific levels only
- Process samples in batches
- Use context manager for cleanup

## Related Files

- `anndiannloader.py`: Base DiannLoader class for loading single files
- `diann_columns.yaml`: Column configuration file
- `diann_collection_loader.py`: Original loader (deprecated, use DiannCollection instead)

## License

This tool is part of the DIA-NN analysis pipeline.
