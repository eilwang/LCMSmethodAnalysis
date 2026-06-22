"""
Precursor-DIA Window Analysis Utilities

Functions for analyzing whether precursors fall within or beyond DIA windows,
enabling assessment of DIA method coverage and identification of missed regions.
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple, Dict, List
import anndata as ad


def check_precursor_in_windows(
    precursor_mz: float,
    precursor_im: float,
    dia_windows: pd.DataFrame
) -> Tuple[bool, Optional[int]]:
    """
    Check if a single precursor falls within any DIA window.

    Parameters:
    -----------
    precursor_mz : float
        Precursor m/z value
    precursor_im : float
        Precursor ion mobility (1/K0) value
    dia_windows : pd.DataFrame
        DataFrame with columns: MzStart, MzEnd, OneOverK0Start, OneOverK0End

    Returns:
    --------
    Tuple[bool, Optional[int]]
        (is_within_window, window_index)
        - is_within_window: True if precursor is in any window
        - window_index: Index of the matching window (or None if not in any window)
    """
    # Check if precursor falls within m/z AND ion mobility range of any window
    mz_matches = (precursor_mz >= dia_windows['MzStart']) & (precursor_mz <= dia_windows['MzEnd'])
    im_matches = (precursor_im >= dia_windows['OneOverK0Start']) & (precursor_im <= dia_windows['OneOverK0End'])

    # Both conditions must be true for a match
    matches = mz_matches & im_matches

    if matches.any():
        # Return True and the index of the first matching window
        return True, matches.idxmax()
    else:
        return False, None


def analyze_sample_coverage(
    sample_obj: ad.AnnData | pd.DataFrame,
    dia_windows: pd.DataFrame,
    mz: str = 'Precursor.Calibrated.Mz',
    im: str = 'Exp.1/K0'
    # use_layers: bool = True
) -> pd.DataFrame:
    """
    Analyze which precursors in a sample fall within DIA windows.

    Parameters:
    -----------
    sample_obj : ad.AnnData or pd.DataFrame
        AnnData object or DataFrame for a single sample (single column from collection)
        Must have precursor m/z and ion mobility data
    dia_windows : pd.DataFrame
        DataFrame with DIA window definitions
        Required columns: MzStart, MzEnd, OneOverK0Start, OneOverK0End
    mz_col : str
        Name of m/z column in layers or obs (default: 'Precursor.Calibrated.Mz')
    im_col : str
        Name of ion mobility column in layers or obs (default: 'Exp.1/K0')
    use_layers : bool
        If True, look for data in layers; if False, look in obs

    Returns:
    --------
    pd.DataFrame
        DataFrame with one row per precursor containing:
        - Original precursor data from obs
        - mz: precursor m/z value
        - im: precursor ion mobility value
        - in_window: Boolean indicating if precursor is in any DIA window
        - window_id: Index of matching window (or -1 if not in any window)
        - distance_to_nearest: Distance to nearest window if not covered
    """
    # Extract precursor m/z and ion mobility values
    # if use_layers:
    #     if mz_col not in sample_adata.layers:
    #         raise ValueError(f"Column '{mz_col}' not found in layers. Available: {list(sample_adata.layers.keys())}")
    #     if im_col not in sample_adata.layers:
    #         raise ValueError(f"Column '{im_col}' not found in layers. Available: {list(sample_adata.layers.keys())}")

    if isinstance(sample_obj, ad.AnnData):
        sample_df = pd.DataFrame({mz: sample_obj.layers[mz_col].flatten(),
                                  im: sample_obj.layers[im_col].flatten()})
        
        sample_df = pd.concat([sample_df, sample_obj.obs.reset_index()], axis=1)

    elif isinstance(sample_obj, pd.DataFrame):
        sample_df = sample_obj.copy()


        # if mz_col not in sample_adata.obs.columns:
        #     raise ValueError(f"Column '{mz_col}' not found in obs. Available: {list(sample_adata.obs.columns)}")
        # if im_col not in sample_adata.obs.columns:
        #     raise ValueError(f"Column '{im_col}' not found in obs. Available: {list(sample_adata.obs.columns)}")

        # mz_values = sample_adata.obs[mz_col].values
        # im_values = sample_adata.obs[im_col].values

    # Remove any NaN values
    sample_df = sample_df.dropna(axis=0, subset=[mz, im])


    # Check each precursor
    sample_df[['in_window', 'window_id']] = sample_df.apply(lambda row: check_precursor_in_windows(row[mz], row[im], dia_windows), axis=1, result_type='expand')
    sample_df['distance_to_nearest'] = sample_df.apply(lambda row: calculate_distance_to_nearest_window(row[mz], row[im], dia_windows) if not row['in_window'] else 0.0, axis=1)
        # result = {
        #     'precursor_idx': i,
        #     'mz': mz,
        #     'im': im,
        #     'in_window': in_window,
        #     'window_id': window_id if window_id is not None else -1
        # }

        # Calculate distance to nearest window if not covered
    
        # if not in_window:
        #     result['distance_to_nearest'] = calculate_distance_to_nearest_window(
        #         mz, im, dia_windows
        #     )
        # else:
        #     result['distance_to_nearest'] = 0.0

        # results.append(result)

    # Convert to DataFrame and merge with original obs data
    # results_df = pd.DataFrame(results)



    return sample_df


def calculate_distance_to_nearest_window(
    precursor_mz: float,
    precursor_im: float,
    dia_windows: pd.DataFrame
) -> float:
    """
    Calculate Euclidean distance to the nearest DIA window.

    Uses normalized distances (m/z and 1/K0 are scaled to [0, 1] range).

    Parameters:
    -----------
    precursor_mz : float
        Precursor m/z value
    precursor_im : float
        Precursor ion mobility (1/K0) value
    dia_windows : pd.DataFrame
        DataFrame with DIA window definitions

    Returns:
    --------
    float
        Normalized Euclidean distance to nearest window
    """
    # Calculate center of each window
    window_mz_center = (dia_windows['MzStart'] + dia_windows['MzEnd']) / 2
    window_im_center = (dia_windows['OneOverK0Start'] + dia_windows['OneOverK0End']) / 2

    # Normalize coordinates to [0, 1] range for fair distance calculation
    mz_range = dia_windows[['MzStart', 'MzEnd']].values.max() - dia_windows[['MzStart', 'MzEnd']].values.min()
    im_range = dia_windows[['OneOverK0Start', 'OneOverK0End']].values.max() - dia_windows[['OneOverK0Start', 'OneOverK0End']].values.min()

    if mz_range == 0 or im_range == 0:
        return np.inf

    # Normalize
    norm_precursor_mz = (precursor_mz - dia_windows[['MzStart', 'MzEnd']].values.min()) / mz_range
    norm_precursor_im = (precursor_im - dia_windows[['OneOverK0Start', 'OneOverK0End']].values.min()) / im_range
    norm_window_mz = (window_mz_center - dia_windows[['MzStart', 'MzEnd']].values.min()) / mz_range
    norm_window_im = (window_im_center - dia_windows[['OneOverK0Start', 'OneOverK0End']].values.min()) / im_range

    # Calculate Euclidean distances
    distances = np.sqrt(
        (norm_precursor_mz - norm_window_mz) ** 2 +
        (norm_precursor_im - norm_window_im) ** 2
    )

    return distances.min()


def summarize_coverage(
    coverage_df: pd.DataFrame,
    intensity_col: Optional[str] = None,
    other_cols: Optional[List[str]] = None
) -> Dict[str, float]:
    """
    Generate summary statistics for DIA window coverage.

    Parameters:
    -----------
    coverage_df : pd.DataFrame
        Output from analyze_sample_coverage
    intensity_col : str, optional
        Name of intensity column in coverage_df for weighted statistics
    other_cols : List[str], optional
        Additional columns in coverage_df to include in the summary

    Returns:
    --------
    Dict[str, float]
        Summary statistics including:
        - total_precursors: Total number of precursors
        - covered_precursors: Number of precursors in DIA windows
        - uncovered_precursors: Number of precursors outside DIA windows
        - coverage_rate: Percentage of precursors covered (by count)
        - coverage_rate_weighted: Percentage covered weighted by intensity (if available)
    """
    total = len(coverage_df)
    covered = coverage_df['in_window'].sum()
    uncovered = total - covered

    summary = {
        'total_precursors': total,
        'covered_precursors': int(covered),
        'uncovered_precursors': int(uncovered),
        'coverage_rate': (covered / total * 100) if total > 0 else 0.0
    }

    if other_cols:
        for c in other_cols:
            temp = coverage_df.groupby(c).agg({'in_window': 'count', c: 'count'})

            print(temp)

            # summary[c] = {'total_precursors': total,
            #               'covered_precursors': int(covered),
            #                 'uncovered_precursors': int(uncovered),
            #                 'coverage_rate': (covered / total * 100) if total > 0 else 0.0}

    # Add weighted coverage if intensity column is provided
    if intensity_col is not None and intensity_col in coverage_df.columns:
        total_intensity = coverage_df[intensity_col].sum()
        covered_intensity = coverage_df[coverage_df['in_window']][intensity_col].sum()

        summary['total_intensity'] = total_intensity
        summary['covered_intensity'] = covered_intensity
        summary['coverage_rate_weighted'] = (
            (covered_intensity / total_intensity * 100) if total_intensity > 0 else 0.0
        )

    return summary


def compare_coverage_across_samples(
    diann_collection: 'DiannCollection',
    ms_method_collection: 'MSMethodCollection',
    level: str = 'precursor',
    mz_col: str = 'Precursor.Calibrated.Mz',
    im_col: str = 'Exp.1/K0',
    ms_method_var: str = 'ms meth'
) -> pd.DataFrame:
    """
    Compare DIA coverage across all samples in a collection.

    Parameters:
    -----------
    diann_collection : DiannCollection
        Collection containing precursor data
    ms_method_collection : MSMethodCollection
        Collection containing MS method/DIA window definitions
    level : str
        Analysis level (default: 'precursor')
    mz_col : str
        Name of m/z column in layers
    im_col : str
        Name of ion mobility column in layers
    ms_method_var : str
        Name of variable in adata.var that contains MS method name

    Returns:
    --------
    pd.DataFrame
        Summary statistics for each sample
    """
    if level not in diann_collection.data:
        raise ValueError(f"Level '{level}' not found in collection")

    adata = diann_collection.data[level]

    # Get list of samples
    samples = adata.var_names.tolist()

    results = []

    for sample in samples:
        # Get sample data (single column)
        sample_adata = adata[:, sample]

        # Get MS method for this sample
        if ms_method_var not in sample_adata.var.columns:
            print(f"Warning: '{ms_method_var}' not found for sample {sample}. Skipping.")
            continue

        ms_method_name = sample_adata.var[ms_method_var].iloc[0]

        if ms_method_name not in ms_method_collection.methods:
            print(f"Warning: MS method '{ms_method_name}' not found in collection. Skipping sample {sample}.")
            continue

        # Get DIA windows
        ms_method = ms_method_collection.methods[ms_method_name]
        dia_windows = ms_method.get_dia_windows()

        if dia_windows is None or len(dia_windows) == 0:
            print(f"Warning: No DIA windows found for method '{ms_method_name}'. Skipping sample {sample}.")
            continue

        # Analyze coverage
        coverage_df = analyze_sample_coverage(
            sample_adata,
            dia_windows,
            mz_col=mz_col,
            im_col=im_col
        )

        # Summarize
        summary = summarize_coverage(coverage_df)
        summary['sample'] = sample
        summary['ms_method'] = ms_method_name

        results.append(summary)

    return pd.DataFrame(results)


# Example usage
if __name__ == "__main__":
    """
    Example workflow:

    # 1. Load your collections
    from diann_collection import DiannCollection
    from ms_method_collection import MSMethodCollection

    bpscollection = DiannCollection.from_file("path/to/collection.pkl")
    mscollection = MSMethodCollection()
    mscollection.add_methods_from_folder("path/to/methods")

    # 2. Analyze a single sample
    sample_adata = bpscollection.data['precursor'][:, 'sample_name']
    dia_windows = mscollection['method_name'].get_dia_windows()

    coverage_df = analyze_sample_coverage(sample_adata, dia_windows)
    summary = summarize_coverage(coverage_df)

    print(f"Coverage: {summary['coverage_rate']:.1f}%")
    print(f"Covered: {summary['covered_precursors']} / {summary['total_precursors']}")

    # 3. Compare across all samples
    comparison = compare_coverage_across_samples(
        bpscollection,
        mscollection,
        ms_method_var='ms meth'
    )
    print(comparison)
    """
    pass
