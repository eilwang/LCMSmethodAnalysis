"""
Filtering utilities for DiannCollection AnnData objects.
"""

import numpy as np
import anndata as ad
from typing import Dict, Tuple, Optional


def filter_collection(
    collection,
    level: str,
    layer_thresholds: Optional[Dict[str, Tuple[float, str]]] = None,
    filter_name: str = 'mask'
):
    """
    Filter an AnnData object based on layer thresholds.

    Parameters:
    -----------
    collection : DiannCollection
        The collection containing the data
    level : str
        The level to filter ('precursor', 'protein', 'gene')
    layer_thresholds : Dict[str, Tuple[float, str]], optional
        Dictionary mapping layer names to (threshold_value, threshold_type) tuples
        - threshold_type can be 'max' or 'min'
        - 'max': keep values <= threshold (filter out values above threshold)
        - 'min': keep values >= threshold (filter out values below threshold)
        Default: {'Q.Value': (0.01, 'max'), 'PG.Q.Value': (0.05, 'max'),
                  'Lib.Q.Value': (0.01, 'max'), 'Lib.PG.Q.Value': (0.05, 'max')}
    filter_name : str
        Name for the mask layer to create (default: 'mask')

    Returns:
    --------
    ad.AnnData
        Filtered AnnData object

    Example:
    --------
    >>> collection = DiannCollection()
    >>> collection.add_from_folder("/path/to/data")
    >>>
    >>> # Default filtering (Q-values)
    >>> filtered = filter_collection(collection, 'precursor')
    >>>
    >>> # Custom filtering
    >>> filtered = filter_collection(
    ...     collection,
    ...     'precursor',
    ...     layer_thresholds={
    ...         'Q.Value': (0.01, 'max'),  # Keep Q-values <= 0.01
    ...         'RT': (10.0, 'min')        # Keep RT >= 10 minutes
    ...     }
    ... )
    """
    # Default thresholds
    if layer_thresholds is None:
        layer_thresholds = {
            'Q.Value': (0.01, 'max'),
            'PG.Q.Value': (0.05, 'max'),
            'Lib.Q.Value': (0.01, 'max'),
            'Lib.PG.Q.Value': (0.05, 'max')
        }

    # Get the AnnData object
    adata = collection.data[level]

    # Initialize mask as all True (keep everything initially)
    mask = np.ones(adata.n_obs, dtype=bool)

    # Apply each threshold
    for layer_name, (threshold_value, threshold_type) in layer_thresholds.items():
        if layer_name not in adata.layers:
            print(f"Warning: Layer '{layer_name}' not found. Skipping.")
            continue

        layer_data = adata.layers[layer_name]

        # Get first column if it's 2D (across all samples)
        if layer_data.ndim == 2:
            # For 2D layers, check if ANY sample passes the threshold
            if threshold_type.lower() == 'max':
                # Keep if ANY value <= threshold (at least one sample passes)
                layer_mask = np.any(layer_data <= threshold_value, axis=1)
            elif threshold_type.lower() == 'min':
                # Keep if ANY value >= threshold (at least one sample passes)
                layer_mask = np.any(layer_data >= threshold_value, axis=1)
            else:
                raise ValueError(f"threshold_type must be 'max' or 'min', got '{threshold_type}'")
        else:
            # For 1D layers
            if threshold_type.lower() == 'max':
                # Keep values <= threshold
                layer_mask = layer_data <= threshold_value
            elif threshold_type.lower() == 'min':
                # Keep values >= threshold
                layer_mask = layer_data >= threshold_value
            else:
                raise ValueError(f"threshold_type must be 'max' or 'min', got '{threshold_type}'")

        # Handle NaN values - exclude them from passing the filter
        layer_mask = layer_mask & ~np.isnan(layer_data if layer_data.ndim == 1 else np.any(np.isnan(layer_data), axis=1))

        # Combine with existing mask (AND logic)
        mask = mask & layer_mask

        print(f"  {layer_name} ({threshold_type} <= {threshold_value}): {layer_mask.sum()} / {len(layer_mask)} pass")

    # Store mask as a layer
    adata.layers[filter_name] = mask

    # Return filtered AnnData
    filtered = adata[mask, :]

    print(f"\nFiltered: {filtered.n_obs} / {adata.n_obs} observations ({100 * filtered.n_obs / adata.n_obs:.1f}%)")

    return filtered


def filter_by_mask(adata: ad.AnnData, mask_layer: str = 'mask') -> ad.AnnData:
    """
    Filter an AnnData object using a pre-computed mask layer.

    Parameters:
    -----------
    adata : ad.AnnData
        The AnnData object to filter
    mask_layer : str
        Name of the layer containing the boolean mask

    Returns:
    --------
    ad.AnnData
        Filtered AnnData object
    """
    if mask_layer not in adata.layers:
        raise KeyError(f"Mask layer '{mask_layer}' not found in AnnData object")

    mask = adata.layers[mask_layer]

    # Handle 2D mask (take any column)
    if mask.ndim == 2:
        mask = np.any(mask, axis=1)

    return adata[mask, :]


def create_quality_mask(
    adata: ad.AnnData,
    q_value_max: float = 0.01,
    pg_q_value_max: float = 0.05,
    lib_q_value_max: float = 0.01,
    lib_pg_q_value_max: float = 0.05,
    mask_name: str = 'quality_mask'
) -> np.ndarray:
    """
    Create a quality filter mask based on common Q-value thresholds.

    Parameters:
    -----------
    adata : ad.AnnData
        The AnnData object
    q_value_max : float
        Maximum Q-value threshold (default: 0.01)
    pg_q_value_max : float
        Maximum protein group Q-value threshold (default: 0.05)
    lib_q_value_max : float
        Maximum library Q-value threshold (default: 0.01)
    lib_pg_q_value_max : float
        Maximum library protein group Q-value threshold (default: 0.05)
    mask_name : str
        Name for the mask layer to create

    Returns:
    --------
    np.ndarray
        Boolean mask array
    """
    mask = np.ones(adata.n_obs, dtype=bool)

    thresholds = {
        'Q.Value': q_value_max,
        'PG.Q.Value': pg_q_value_max,
        'Lib.Q.Value': lib_q_value_max,
        'Lib.PG.Q.Value': lib_pg_q_value_max
    }

    for layer_name, threshold in thresholds.items():
        if layer_name in adata.layers:
            layer_data = adata.layers[layer_name]

            # Handle 2D arrays
            if layer_data.ndim == 2:
                layer_mask = np.any(layer_data <= threshold, axis=1)
            else:
                layer_mask = layer_data <= threshold

            # Exclude NaN values
            if layer_data.ndim == 2:
                layer_mask = layer_mask & ~np.all(np.isnan(layer_data), axis=1)
            else:
                layer_mask = layer_mask & ~np.isnan(layer_data)

            mask = mask & layer_mask

    # Store mask in layers
    adata.layers[mask_name] = mask

    return mask
