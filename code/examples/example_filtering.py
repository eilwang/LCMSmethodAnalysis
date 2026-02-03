"""Example demonstrating filtering functionality for DiannCollection."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from diann_collection import DiannCollection
from code.archive.filter_utils import filter_collection, create_quality_mask, filter_by_mask
import numpy as np

print("Example: Filtering DiannCollection Data")
print("=" * 80)

# Load collection
collection = DiannCollection()
collection.add_from_folder("/Users/eileen.wang/Desktop/diann/SampleData/BPS", search_type='bps')

print("\nOriginal data shape:", collection.data['precursor'].shape)

# Example 1: Default quality filtering (Q-values)
print("\n" + "=" * 80)
print("Example 1: Default Quality Filtering")
print("=" * 80)

filtered1 = filter_collection(collection, 'precursor')
print(f"Filtered shape: {filtered1.shape}")

# Example 2: Custom thresholds
print("\n" + "=" * 80)
print("Example 2: Custom Thresholds")
print("=" * 80)

filtered2 = filter_collection(
    collection,
    'precursor',
    layer_thresholds={
        'Q.Value': (0.01, 'max'),      # Keep Q-values <= 0.01 (high confidence)
        'Lib.Q.Value': (0.01, 'max'),  # Keep library Q-values <= 0.01
        'RT': (10.0, 'min'),           # Keep RT >= 10 minutes (min threshold)
        'RT.Stop': (50.0, 'max')       # Keep RT.Stop <= 50 minutes (max threshold)
    }
)
print(f"Filtered shape: {filtered2.shape}")

# Example 3: Using mask directly
print("\n" + "=" * 80)
print("Example 3: Create and Apply Mask Separately")
print("=" * 80)

adata = collection.data['precursor']

# Create quality mask
mask = create_quality_mask(
    adata,
    q_value_max=0.01,
    pg_q_value_max=0.05,
    mask_name='quality_mask'
)

print(f"Mask created: {mask.sum()} / {len(mask)} observations pass")

# Apply mask
filtered3 = filter_by_mask(adata, mask_layer='quality_mask')
print(f"Filtered shape: {filtered3.shape}")

# Example 4: Threshold type explanation
print("\n" + "=" * 80)
print("Example 4: Understanding 'max' vs 'min' Threshold Types")
print("=" * 80)

print("\n'max' threshold: Keep values BELOW OR EQUAL to threshold")
print("  Example: Q.Value with (0.01, 'max') -> keeps Q.Value <= 0.01")
print("  Use case: Quality metrics where lower = better")

print("\n'min' threshold: Keep values ABOVE OR EQUAL to threshold")
print("  Example: RT with (10.0, 'min') -> keeps RT >= 10.0")
print("  Use case: Intensity, RT range, or any metric where higher = better")

# Example 5: Multiple sample filtering
print("\n" + "=" * 80)
print("Example 5: Filtering Across Multiple Samples")
print("=" * 80)

print("\nFor 2D layer data (n_obs × n_samples):")
print("  - 'max' threshold: Keep if ANY sample has value <= threshold")
print("  - 'min' threshold: Keep if ANY sample has value >= threshold")
print("\nThis means a precursor is kept if it passes the filter in at least one sample.")

filtered5 = filter_collection(
    collection,
    'precursor',
    layer_thresholds={
        'Q.Value': (0.01, 'max'),  # Keep if any sample has Q.Value <= 0.01
    }
)
print(f"Filtered shape: {filtered5.shape}")

print("\n" + "=" * 80)
print("Filtering examples complete!")
print("=" * 80)
