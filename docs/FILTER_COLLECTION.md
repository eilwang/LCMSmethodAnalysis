# DiannCollection Filtering Guide

## Quick Reference

Filter AnnData objects in DiannCollection based on quality metrics (Q-values), retention time, or any layer values.

## Core Concept: 'max' vs 'min' Thresholds

### 'max' threshold
**Keep values ≤ threshold** (filter out values above threshold)

Use for metrics where **lower is better**:
- Q-values (quality scores)
- P-values
- Error rates
- Upper bounds for RT, m/z, etc.

```python
layer_thresholds = {
    'Q.Value': (0.01, 'max')  # Keep Q.Value <= 0.01 (high confidence)
}
```

### 'min' threshold
**Keep values ≥ threshold** (filter out values below threshold)

Use for metrics where **higher is better**:
- Intensity values
- Scores/confidence
- Lower bounds for RT, m/z, etc.

```python
layer_thresholds = {
    'Precursor.Quantity': (1000.0, 'min'),  # Keep intensity >= 1000
    'RT': (10.0, 'min')                      # Keep RT >= 10 minutes
}
```

## Basic Usage

```python
from diann_collection import DiannCollection
from filter_utils import filter_collection

# Load data
collection = DiannCollection()
collection.add_from_folder("/path/to/data", search_type='bps')

# Filter with defaults (Q-value thresholds)
filtered = filter_collection(collection, 'precursor')
```

**Default thresholds:**
```python
{
    'Q.Value': (0.01, 'max'),           # Precursor Q-value <= 0.01
    'PG.Q.Value': (0.05, 'max'),        # Protein group Q-value <= 0.05
    'Lib.Q.Value': (0.01, 'max'),       # Library Q-value <= 0.01
    'Lib.PG.Q.Value': (0.05, 'max')     # Library PG Q-value <= 0.05
}
```

## Custom Filtering Examples

### Example 1: Stricter Q-value Threshold

```python
filtered = filter_collection(
    collection,
    'precursor',
    layer_thresholds={
        'Q.Value': (0.001, 'max')  # Only keep Q-value <= 0.001 (very high confidence)
    }
)
```

### Example 2: RT Range Filter

```python
# Keep precursors between 10 and 50 minutes
filtered = filter_collection(
    collection,
    'precursor',
    layer_thresholds={
        'RT': (10.0, 'min'),      # RT >= 10 minutes
        'RT.Stop': (50.0, 'max')  # RT <= 50 minutes
    }
)
```

### Example 3: Quality + Intensity Filter

```python
filtered = filter_collection(
    collection,
    'precursor',
    layer_thresholds={
        'Q.Value': (0.01, 'max'),              # High quality
        'Precursor.Quantity': (1000.0, 'min')  # Sufficient intensity
    }
)
```

### Example 4: Multiple Metrics

```python
filtered = filter_collection(
    collection,
    'precursor',
    layer_thresholds={
        'Q.Value': (0.01, 'max'),
        'Lib.Q.Value': (0.01, 'max'),
        'RT': (5.0, 'min'),
        'RT.Stop': (60.0, 'max'),
        'Precursor.Quantity': (500.0, 'min'),
        'Evidence': (3, 'min')  # At least 3 data points
    }
)
```

## Multi-Sample Filtering

For 2D layer data (n_obs × n_samples):
- **'max' threshold**: Keep if **ANY** sample has value ≤ threshold
- **'min' threshold**: Keep if **ANY** sample has value ≥ threshold

This means a precursor/protein is kept if it passes the filter in **at least one sample**.

```python
# Keep precursors that have Q.Value <= 0.01 in ANY sample
filtered = filter_collection(
    collection,
    'precursor',
    layer_thresholds={
        'Q.Value': (0.01, 'max')
    }
)
```

## Working with Masks

### Create a Mask Without Filtering

```python
from filter_utils import create_quality_mask

adata = collection.data['precursor']

# Create mask (stored in layers)
mask = create_quality_mask(
    adata,
    q_value_max=0.01,
    pg_q_value_max=0.05,
    mask_name='quality_mask'
)

print(f"{mask.sum()} / {len(mask)} pass quality filter")

# Inspect mask
print(f"Mask stored in layers: {adata.layers['quality_mask']}")
```

### Apply Pre-computed Mask

```python
from filter_utils import filter_by_mask

# Apply the mask to filter data
filtered = filter_by_mask(adata, mask_layer='quality_mask')
```

## Available Layers for Filtering

Common layers in DIA-NN data:

### Quality Metrics (use 'max')
- `Q.Value` - Precursor Q-value
- `PG.Q.Value` - Protein group Q-value
- `Lib.Q.Value` - Library Q-value
- `Lib.PG.Q.Value` - Library protein group Q-value
- `Quantity.Quality` - Quantification quality

### Quantification (use 'min' for thresholds)
- `Precursor.Quantity` - Precursor intensity
- `Precursor.Normalised` - Normalized intensity
- `Ms1.Area` - MS1 area

### Retention Time (use 'min' or 'max' for ranges)
- `RT` - Retention time
- `RT.Start` - RT start
- `RT.Stop` - RT end
- `iRT` - Indexed RT
- `Predicted.RT` - Predicted RT

### Scoring (use 'min' for thresholds)
- `Evidence` - Number of data points
- `CScore` - Confidence score
- `Ms1.Profile.Corr` - MS1 profile correlation

## Function Reference

### filter_collection()

```python
filter_collection(
    collection,                    # DiannCollection object
    level: str,                    # 'precursor', 'protein', or 'gene'
    layer_thresholds: Dict = None, # {layer_name: (threshold, type)}
    filter_name: str = 'mask'      # Name for mask layer
) -> ad.AnnData
```

**Parameters:**
- `collection`: DiannCollection object
- `level`: Analysis level to filter
- `layer_thresholds`: Dictionary of {layer: (value, 'max'|'min')}
- `filter_name`: Name for the boolean mask layer

**Returns:**
- Filtered AnnData object

### create_quality_mask()

```python
create_quality_mask(
    adata: ad.AnnData,
    q_value_max: float = 0.01,
    pg_q_value_max: float = 0.05,
    lib_q_value_max: float = 0.01,
    lib_pg_q_value_max: float = 0.05,
    mask_name: str = 'quality_mask'
) -> np.ndarray
```

**Parameters:**
- `adata`: AnnData object to create mask for
- `q_value_max`: Maximum Q-value threshold
- `pg_q_value_max`: Maximum protein group Q-value
- `lib_q_value_max`: Maximum library Q-value
- `lib_pg_q_value_max`: Maximum library PG Q-value
- `mask_name`: Name for the mask layer

**Returns:**
- Boolean numpy array mask

### filter_by_mask()

```python
filter_by_mask(
    adata: ad.AnnData,
    mask_layer: str = 'mask'
) -> ad.AnnData
```

**Parameters:**
- `adata`: AnnData object with a mask layer
- `mask_layer`: Name of the boolean mask layer

**Returns:**
- Filtered AnnData object

## Common Workflows

### Workflow 1: Standard Quality Filter

```python
# Standard 1% FDR filter
filtered = filter_collection(
    collection,
    'precursor',
    layer_thresholds={
        'Q.Value': (0.01, 'max'),
        'Lib.Q.Value': (0.01, 'max')
    }
)

print(f"Filtered: {filtered.n_obs} precursors")
```

### Workflow 2: Custom Range Filter

```python
# Keep precursors in a specific RT and m/z range
filtered = filter_collection(
    collection,
    'precursor',
    layer_thresholds={
        'Q.Value': (0.01, 'max'),
        'RT': (15.0, 'min'),
        'RT.Stop': (45.0, 'max')
    }
)
```

### Workflow 3: Intensity-based Filter

```python
# Keep high-quality, high-intensity precursors
filtered = filter_collection(
    collection,
    'precursor',
    layer_thresholds={
        'Q.Value': (0.01, 'max'),
        'Precursor.Quantity': (10000.0, 'min'),
        'Evidence': (5, 'min')
    }
)
```

### Workflow 4: Progressive Filtering

```python
# Apply filters progressively and inspect results
adata = collection.data['precursor']

# Step 1: Quality filter
filtered1 = filter_collection(
    collection, 'precursor',
    layer_thresholds={'Q.Value': (0.01, 'max')}
)
print(f"After quality filter: {filtered1.n_obs}")

# Step 2: Add intensity filter to quality-filtered data
# (Create a new temporary collection)
from diann_collection import DiannCollection
temp_collection = DiannCollection()
temp_collection.data['precursor'] = filtered1

filtered2 = filter_collection(
    temp_collection, 'precursor',
    layer_thresholds={'Precursor.Quantity': (1000.0, 'min')}
)
print(f"After intensity filter: {filtered2.n_obs}")
```

## Troubleshooting

### Warning: "Layer not found"
If you see: `Warning: Layer 'X' not found. Skipping.`

Check available layers:
```python
adata = collection.data['precursor']
print(adata.layers.keys())
```

### NaN Handling
NaN values are automatically excluded from passing filters. If all values are NaN for a layer, the observation will be filtered out.

### 2D vs 1D Layers
- **1D layers**: Single value per observation (e.g., some metadata)
- **2D layers**: One value per observation per sample (most quantitative data)

The function automatically handles both cases.

## Performance Tips

1. **Filter early**: Apply quality filters before intensive computations
2. **Combine filters**: Use multiple thresholds in one call rather than sequential filtering
3. **Save filtered data**: Store frequently-used filtered datasets

```python
# Filter once, save for reuse
filtered = filter_collection(collection, 'precursor')
filtered.write_h5ad('filtered_precursor.h5ad')

# Load later
import anndata as ad
filtered = ad.read_h5ad('filtered_precursor.h5ad')
```
