"""
New find_differences method that returns a single unified DataFrame.
This will replace the existing method in ms_method_collection.py
"""

def find_differences(self, method_names: Optional[List[str]] = None,
                    include_params: bool = True,
                    include_polarity_configs: bool = True,
                    include_dia: bool = True,
                    polarities: Optional[List[str]] = None,
                    sources: Optional[List[str]] = None,
                    tolerance: float = 1e-6) -> pd.DataFrame:
    """
    Find differences between methods and return as single unified DataFrame.

    Parameters:
    -----------
    method_names : List[str], optional
        Methods to compare. If None, compare all methods.
    include_params : bool
        Whether to check global MS instrument parameters (default: True)
    include_polarity_configs : bool
        Whether to check polarity-specific parameters (default: True)
    include_dia : bool
        Whether to check DIA settings (default: True)
    polarities : List[str], optional
        Specific polarities to compare ('positive', 'negative').
    sources : List[str], optional
        Specific ion sources to compare ('esi', 'captivespray', 'apci', etc.).
    tolerance : float
        Tolerance for floating point comparisons (default: 1e-6)

    Returns:
    --------
    pd.DataFrame
        DataFrame with all differences. Columns:
        - 'Parameter': parameter name
        - 'Type': 'instrument_param', 'polarity_param', 'dia_stat', or 'dia_windows'
        - One column per method with the values
        - 'Description': optional description

    Example:
    --------
    # Compare all settings
    diff_df = collection.find_differences(['method1', 'method2'])

    # Filter by type
    instrument_diffs = diff_df[diff_df['Type'] == 'instrument_param']
    dia_diffs = diff_df[diff_df['Type'].str.startswith('dia_')]
    """
    if method_names is None:
        method_names = self.list_methods()

    if len(method_names) < 2:
        return pd.DataFrame({'Message': ['Need at least 2 methods to compare']})

    rows = []

    # Compare global MS instrument parameters
    if include_params:
        param_diffs = self._find_param_differences(method_names, tolerance,
                                                  check_polarity_configs=False)
        for param_name, values_list in param_diffs.items():
            row = {
                'Parameter': param_name,
                'Type': 'instrument_param',
                'Description': ''
            }
            for method_name, value in values_list:
                row[method_name] = value
            rows.append(row)

    # Compare polarity-specific parameters (positive only)
    if include_polarity_configs:
        polarity_diffs = self._find_polarity_differences(method_names, tolerance,
                                                         polarities, sources)
        for param_key, values_list in polarity_diffs.items():
            # Parse key: polarity_source_param
            parts = param_key.split('_', 2)
            if len(parts) >= 3:
                polarity, source, param_name = parts[0], parts[1], parts[2]
            else:
                polarity, source, param_name = 'unknown', 'unknown', param_key

            row = {
                'Parameter': f"{source}_{param_name}",
                'Type': 'polarity_param',
                'Description': f'{polarity} polarity'
            }
            for method_name, value in values_list:
                row[method_name] = value
            rows.append(row)

    # Compare DIA settings comprehensively
    if include_dia:
        dia_rows = self._compare_dia_comprehensive(method_names, tolerance)
        rows.extend(dia_rows)

    if not rows:
        return pd.DataFrame({'Message': ['Methods are identical']})

    # Create DataFrame
    df = pd.DataFrame(rows)

    # Reorder columns: Parameter, Type, Description, then all methods
    cols = ['Parameter', 'Type', 'Description'] + [m for m in method_names if m in df.columns]
    df = df[[c for c in cols if c in df.columns]]

    return df


def _compare_dia_comprehensive(self, method_names: List[str], tolerance: float) -> List[Dict]:
    """
    Comprehensive DIA comparison including stats and window placement.

    Returns list of row dicts for DataFrame construction.
    """
    rows = []

    # Check if all methods have DIA
    has_dia = {}
    for name in method_names:
        if name in self.methods:
            method_dict = self.methods[name].to_flat_dict(polarity='positive')
            has_dia[name] = method_dict.get('has_dia', False)

    if not all(has_dia.values()):
        row = {
            'Parameter': 'has_dia',
            'Type': 'dia_stat',
            'Description': 'Method has DIA configured'
        }
        for name in method_names:
            row[name] = has_dia.get(name, False)
        rows.append(row)
        return rows  # Stop comparison if not all have DIA

    # Compare DIA statistics from flat dicts
    dia_stats = [
        ('dia_window_count', 'Number of DIA windows'),
        ('dia_cycle_count', 'Number of PASEF cycles'),
        ('dia_mz_min', 'm/z minimum'),
        ('dia_mz_max', 'm/z maximum'),
        ('dia_im_min', '1/K0 minimum'),
        ('dia_im_max', '1/K0 maximum'),
    ]

    for stat_key, description in dia_stats:
        values = {}
        for name in method_names:
            if name in self.methods:
                method_dict = self.methods[name].to_flat_dict(polarity='positive')
                values[name] = method_dict.get(stat_key)

        # Check if values differ
        unique_vals = set(v for v in values.values() if v is not None)
        if len(unique_vals) > 1:
            row = {
                'Parameter': stat_key,
                'Type': 'dia_stat',
                'Description': description
            }
            row.update(values)
            rows.append(row)

    # Compare window placement (if windows exist and counts are the same)
    window_counts = {}
    for name in method_names:
        if name in self.methods:
            method_dict = self.methods[name].to_flat_dict(polarity='positive')
            window_counts[name] = method_dict.get('dia_window_count', 0)

    # If all have same number of windows, compare window-by-window
    if len(set(window_counts.values())) == 1 and list(window_counts.values())[0] > 0:
        windows_differ = False

        # Get windows from each method
        all_windows = {}
        for name in method_names:
            if name in self.methods:
                method_dict = self.methods[name].to_flat_dict(polarity='positive')
                all_windows[name] = method_dict.get('dia_windows')

        # Compare window-by-window
        num_windows = list(window_counts.values())[0]
        ref_name = method_names[0]
        ref_windows = all_windows[ref_name]

        for idx in range(num_windows):
            for col in ['MzStart', 'MzEnd', 'OneOverK0Start', 'OneOverK0End', 'CycleId']:
                if col not in ref_windows.columns:
                    continue

                ref_val = ref_windows.iloc[idx][col]
                values = {ref_name: ref_val}

                for name in method_names[1:]:
                    if name in all_windows and all_windows[name] is not None:
                        other_windows = all_windows[name]
                        if idx < len(other_windows):
                            values[name] = other_windows.iloc[idx][col]

                # Check if different (accounting for NaN)
                unique_vals = []
                for v in values.values():
                    if pd.isna(v):
                        continue
                    if isinstance(v, (int, float)):
                        comparable = round(v / tolerance) * tolerance
                    else:
                        comparable = v
                    if comparable not in unique_vals:
                        unique_vals.append(comparable)

                if len(unique_vals) > 1:
                    windows_differ = True
                    row = {
                        'Parameter': f'window_{idx}_{col}',
                        'Type': 'dia_window_param',
                        'Description': f'Window {idx} {col}'
                    }
                    row.update(values)
                    rows.append(row)

        # If windows differ, add a summary row with actual windows DataFrames
        if windows_differ:
            row = {
                'Parameter': 'dia_windows',
                'Type': 'dia_windows',
                'Description': 'Complete DIA window specifications (DataFrame objects)'
            }
            for name in method_names:
                row[name] = all_windows.get(name, None)
            rows.append(row)

    return rows
