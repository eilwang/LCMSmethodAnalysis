"""
MS Method Collection for Bruker TimsTOF Methods

This module provides collection and comparison capabilities for multiple
Bruker TimsTOF method files, enabling batch processing and systematic
comparison of instrument parameters and acquisition settings.
"""

import pandas as pd
import pickle
import json
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple
from collections import defaultdict
import zipfile
import tempfile

from bruker_method import BrukerMethod


class MSMethodCollection:
    """Collection of MS methods with storage and comparison capabilities."""

    def __init__(self):
        """Initialize empty method collection."""
        self.methods: Dict[str, BrukerMethod] = {}

    @classmethod
    def from_file(cls, filepath: str) -> 'MSMethodCollection':
        """
        Create a new collection from a saved file.

        Parameters:
        -----------
        filepath : str
            Path to saved collection file (.pkl, .json)

        Returns:
        --------
        MSMethodCollection
            New collection loaded from file

        Example:
        --------
        collection = MSMethodCollection.from_file('methods.pkl')
        """
        collection = cls()
        collection.load(filepath)
        return collection

    def add_method(self, method: Union[str, BrukerMethod],
                   name: Optional[str] = None,
                   overwrite: str = 'ignore'):
        """
        Add a method to the collection.

        Parameters:
        -----------
        method : str or BrukerMethod
            Path to .m directory/.zip file or BrukerMethod object
        name : str, optional
            Identifier for the method. If None, automatically extracts from file path.
            For paths ending in .m: removes .m extension (e.g., DIA003.proteoscape.m → DIA003.proteoscape)
            For paths ending in .zip: removes .zip extension (e.g., DIA015.m.zip → DIA015.m)
        overwrite : str
            'ignore': Skip if method already exists (default)
            'allow': Overwrite existing method
            Other: Raise error if method already exists
        """
        # Auto-extract name from path if not provided
        method_path = None
        if name is None:
            if isinstance(method, str):
                method_path = Path(method)
                name = method_path.stem
            else:
                raise ValueError("name parameter is required when passing a BrukerMethod object")
        elif isinstance(method, str):
            method_path = Path(method)

        # Check for duplicates
        if name in self.methods:
            if overwrite == 'ignore':
                if method_path:
                    print(f"Warning: Method '{name}' already exists. Skipping: {method_path.name}")
                else:
                    print(f"Warning: Method '{name}' already exists. Skipping addition.")
                return
            elif overwrite == 'allow':
                if method_path:
                    print(f"Warning: Overwriting method '{name}' with: {method_path.name}")
                else:
                    print(f"Warning: Overwriting method '{name}'")
            else:
                raise ValueError(
                    f"Method '{name}' already exists in collection. "
                    f"Use overwrite='allow' to replace it or remove_method() first."
                )

        if isinstance(method, str):
            method = BrukerMethod(method)
        self.methods[name] = method

    def add_methods_from_paths(self, method_paths: Union[List[str], Dict[str, str]],
                               overwrite: bool = False):
        """
        Add multiple methods from file paths.

        Parameters:
        -----------
        method_paths : List[str] or Dict[str, str]
            List of paths to .m directories or .zip files (names auto-extracted), OR
            Dictionary mapping custom names to paths (for backward compatibility)
        overwrite : bool
            If True, overwrite existing methods with same names.
            If False, raise error if any method already exists.

        Examples:
        ---------
        # List of paths (names auto-extracted)
        collection.add_methods_from_paths([
            '/path/to/DIA003.m',
            '/path/to/DIA015.m.zip'
        ])

        # Dictionary with custom names (backward compatible)
        collection.add_methods_from_paths({
            'Custom1': '/path/to/method1.m',
            'Custom2': '/path/to/method2.m'
        })
        """
        # Handle list of paths (new preferred API)
        if isinstance(method_paths, list):
            for path in method_paths:
                self.add_method(path, overwrite='allow' if overwrite else 'ignore')
        # Handle dict of name->path (backward compatibility)
        elif isinstance(method_paths, dict):
            for name, path in method_paths.items():
                self.add_method(path, name=name, overwrite='allow' if overwrite else 'ignore')
        else:
            raise TypeError("method_paths must be a list of paths or a dict of name->path mappings")

    def add_methods_from_folder(self, folder_path: str,
                                overwrite: bool = False):
        """
        Add multiple methods from a folder or zip file.

        Can accept:
        - A folder containing .m directories and/or .zip files
        - A zip file directly (will extract all methods inside)

        For .zip files containing multiple methods:
        - Each method is loaded with its own name

        Parameters:
        -----------
        folder_path : str
            Path to folder containing .m directories or .zip files, OR
            Path to a .zip file containing multiple .m directories
            overwrite : bool
            If True, overwrite existing methods with same names.
            If False, raise error if any method already exists.
        """

        path = Path(folder_path)
        all_methods = {}

        # Check if the path itself is a zip file
        if path.suffix == '.zip' and path.is_file():
            # Process the zip file directly
            try:
                with zipfile.ZipFile(path, 'r') as zf:
                    # Find all .m directories in the zip
                    all_names = zf.namelist()
                    m_dirs_in_zip = set()

                    for name in all_names:
                        # Look for .m directory markers
                        if '.m/' in name and not name.startswith('__MACOSX'):
                            # Extract the .m directory name
                            m_dir_name = name.split('.m/')[0] + '.m'
                            m_dirs_in_zip.add(m_dir_name)

                    if len(m_dirs_in_zip) == 0:
                        print(f"Warning: No .m directories found in {path.name}")
                        return

                    # Extract to temp directory
                    temp_dir = tempfile.mkdtemp(prefix='ms_methods_')
                    try:
                        zf.extractall(temp_dir)

                        # Add each method found in the zip
                        for m_dir_name in m_dirs_in_zip:
                            # Get clean name
                            clean_name = Path(m_dir_name).stem
                            full_path = Path(temp_dir) / m_dir_name

                            if full_path.exists() and full_path.is_dir():
                                all_methods[clean_name] = str(full_path)
                    except Exception as e:
                        print(f"Warning: Error extracting methods from {path.name}: {e}")
            except zipfile.BadZipFile:
                print(f"Warning: {path.name} is not a valid zip file")
                return

            self.add_methods_from_paths(all_methods, overwrite=overwrite)
            return

        # Otherwise, treat as a folder
        folder = path
        if not folder.is_dir():
            raise ValueError(f"Path is not a folder or zip file: {folder_path}")

        # Find .m directories directly in folder
        m_dirs = {f.stem: str(f) for f in folder.glob("*.m") if f.is_dir()}
        all_methods.update(m_dirs)

        # Find .zip files and extract methods from inside them
        for zip_file in folder.glob("*.zip"):
            try:
                with zipfile.ZipFile(zip_file, 'r') as zf:
                    # Find all .m directories in the zip
                    all_names = zf.namelist()
                    m_dirs_in_zip = set()

                    for name in all_names:
                        # Look for .m directory markers
                        if '.m/' in name and not name.startswith('__MACOSX'):
                            # Extract the .m directory name
                            m_dir_name = name.split('.m/')[0] + '.m'
                            m_dirs_in_zip.add(m_dir_name)

                    if len(m_dirs_in_zip) == 0:
                        print(f"Warning: No .m directories found in {zip_file.name}")
                        continue

                    # Extract to temp directory
                    temp_dir = tempfile.mkdtemp(prefix='ms_methods_')
                    try:
                        zf.extractall(temp_dir)

                        # Add each method found in the zip
                        for m_dir_name in m_dirs_in_zip:
                            # Get clean name
                            clean_name = Path(m_dir_name).stem
                            full_path = Path(temp_dir) / m_dir_name

                            if full_path.exists() and full_path.is_dir():
                                # If this zip only has one method, use zip name
                                if len(m_dirs_in_zip) == 1:
                                    method_name = zip_file.stem
                                else:
                                    method_name = clean_name

                                all_methods[method_name] = str(full_path)
                    except Exception as e:
                        print(f"Warning: Error extracting methods from {zip_file.name}: {e}")
                        continue
            except zipfile.BadZipFile:
                print(f"Warning: {zip_file.name} is not a valid zip file, skipping")
                continue

        self.add_methods_from_paths(all_methods, overwrite=overwrite)

    def get_method(self, name: str) -> Optional[BrukerMethod]:
        """Get method by name."""
        return self.methods.get(name)

    def list_methods(self) -> List[str]:
        """List all method names."""
        return list(self.methods.keys())

    def remove_method(self, name: str):
        """Remove method from collection."""
        if name in self.methods:
            del self.methods[name]

    def summary_df(self) -> pd.DataFrame:
        """
        Create summary DataFrame of all methods.

        Returns:
        --------
        pd.DataFrame
            Summary with method name, key parameters, DIA info
        """
        summary_data = []
        for name, method in self.methods.items():
            row = {
                'Method': name}
                # 'MS Params': len(method.ms.instrument_params),
                # 'Polarities': ', '.join(method.ms.polarity_configs.keys()),
                # 'Has DIA': method.dia is not None,
                # 'Has Synchro': method.synchro is not None and not method.synchro.is_empty,


            # Add some key parameters
            # row['Collision Gas'] = method.get_param('Collision_GasSupply_Set')
            # row['Digitizer Sample Interval'] = method.get_param('Digitizer_SampleIntervall')
            row['TOF Detector'] = method.get_param('TOF_DetectorTofSetValue')
            # Note: CaptiveSpray doesn't have Source_CapillarySetValue parameter
            # Using Transfer_CapillaryExit_Base_Set from default source instead
            row['Capillary Exit Voltage (Pos) [V]'] = method.get_param('Transfer_CapillaryExit_Base_Set', polarity='positive', source='default')

            # Timing parameters for ramp rate calculation
            # Note: Using IMS_imeX_RampTime (4th value from vector) for positive polarity
            row['IMS Ramp Time [ms]'] = method.get_ims_imex_ramp_time(polarity='positive')
            row['Focus PreTOF Transfer Time [us]'] = method.get_param('Calibration_FocusPreTOF_Lens1_TransferTime', polarity='positive', source='default')
            row['Focus PreTOF PrePulse Storage [us]'] = method.get_param('Calibration_FocusPreTOF_Lens1_PrePulseStorageTime', polarity='positive', source='default')

            # Calculate ramp rate in Hz
            ramp_time_ms = row['IMS Ramp Time [ms]']
            transfer_time_us = row['Focus PreTOF Transfer Time [us]']
            prepulse_storage_us = row['Focus PreTOF PrePulse Storage [us]']

            if all(v is not None for v in [ramp_time_ms, transfer_time_us, prepulse_storage_us]):
                # Convert ramp time from ms to us, sum all times, convert to Hz
                total_time_us = (ramp_time_ms * 1000.0) + transfer_time_us + prepulse_storage_us
                row['Ramp Rate [Hz]'] = 1000000.0 / total_time_us
            else:
                row['Ramp Rate [Hz]'] = None


            # DIA parameters (only PASEF frames, excluding MS1)
            if method.dia:
                dia_windows = method.get_dia_windows()
                if len(dia_windows) > 0:
                    dia_cycle_ids = method.get_dia_cycle_ids()
                    num_cycles = len(dia_cycle_ids) if dia_cycle_ids else 0

                    row['DIA Total Windows'] = len(dia_windows)
                    row['DIA PASEF Cycles'] = num_cycles
                    row['DIA Windows per Cycle'] = len(dia_windows) // num_cycles if num_cycles > 0 else 0
                    row['DIA m/z Min'] = dia_windows['MzStart'].min()
                    row['DIA m/z Max'] = dia_windows['MzEnd'].max()
                    row['DIA Ion Mobility Min (1/K0)'] = dia_windows['OneOverK0Start'].min()
                    row['DIA Ion Mobility Max (1/K0)'] = dia_windows['OneOverK0End'].max()

                    # Calculate cycle time: number of cycles / ramp rate
                    ramp_rate = row['Ramp Rate [Hz]']
                    if ramp_rate is not None and num_cycles > 0:
                        row['Cycle Time [s]'] = num_cycles / ramp_rate
                    else:
                        row['Cycle Time [s]'] = None
                else:
                    row['DIA Total Windows'] = 0
                    row['DIA PASEF Cycles'] = 0
                    row['DIA Windows per Cycle'] = 0
                    row['DIA m/z Min'] = None
                    row['DIA m/z Max'] = None
                    row['DIA Ion Mobility Min (1/K0)'] = None
                    row['DIA Ion Mobility Max (1/K0)'] = None
                    row['Cycle Time [s]'] = None
            else:
                row['DIA Total Windows'] = 0
                row['DIA PASEF Cycles'] = 0
                row['DIA Windows per Cycle'] = 0
                row['DIA m/z Min'] = None
                row['DIA m/z Max'] = None
                row['DIA Ion Mobility Min (1/K0)'] = None
                row['DIA Ion Mobility Max (1/K0)'] = None
                row['Cycle Time [s]'] = None

            summary_data.append(row)

        return pd.DataFrame(summary_data)

    def compare_parameters(self, param_names: List[str],
                          polarity: Optional[str] = None,
                          source: str = 'default',
                          method_names: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Compare specific parameters across methods.

        Parameters:
        -----------
        param_names : List[str]
            List of parameter names to compare
        polarity : Optional[str]
            'positive', 'negative', or None for global parameters
        source : str
            Ion source ('esi', 'apci', etc.), default is 'default'
        method_names : List[str], optional
            Methods to compare. If None, compare all methods.

        Returns:
        --------
        pd.DataFrame
            Comparison table with methods as rows and parameters as columns
        """
        if method_names is None:
            method_names = self.list_methods()

        comparison_data = []
        for name in method_names:
            if name in self.methods:
                method = self.methods[name]
                row = {'Method': name}

                for param_name in param_names:
                    value = method.get_param(param_name, polarity=polarity, source=source)
                    row[param_name] = value

                comparison_data.append(row)

        return pd.DataFrame(comparison_data)

    def plot_windows(self, method_names: Optional[List[str]] = None,
                    color_by_method: bool = True,
                    alpha: float = 0.6,
                    edge_color: str = 'white',
                    figsize=(14, 8),
                    show_labels: bool = False,
                    ax=None):
        """
        Plot DIA windows from multiple methods overlaid on same axis.

        Parameters:
        -----------
        method_names : List[str], optional
            Methods to plot. If None, plots all methods.
        color_by_method : bool
            If True, each method gets a unique color. If False, color by cycle ID (default: True)
        alpha : float
            Transparency of window fills, 0-1 (default: 0.6)
        edge_color : str
            Color of window outlines (default: 'white')
        figsize : tuple
            Figure size (default: (14, 8)), only used if ax is None
        show_labels : bool
            Whether to show cycle ID labels on windows (default: False)
        ax : matplotlib.axes.Axes, optional
            Axes to plot on. If None, creates a new figure.

        Returns:
        --------
        matplotlib.axes.Axes
            The axis object with the plot
        """
        import matplotlib.pyplot as plt
        import matplotlib.cm as cm
        from matplotlib.patches import Patch

        if method_names is None:
            method_names = self.list_methods()

        # Filter out methods without DIA settings
        methods_with_dia = []
        for name in method_names:
            if name in self.methods and self.methods[name].dia is not None:
                methods_with_dia.append(name)

        if not methods_with_dia:
            print("Warning: No methods with DIA settings found")
            return None

        # Create figure if ax not provided
        created_fig = ax is None
        if ax is None:
            fig, ax = plt.subplots(figsize=figsize)

        # Define colors for each method
        if color_by_method:
            colors = cm.tab10(range(len(methods_with_dia)))

        # Create legend handles
        legend_handles = []

        # Plot each method
        for i, name in enumerate(methods_with_dia):
            method = self.methods[name]

            if color_by_method:
                # Use method-specific color
                method.plot_windows(
                    ax=ax,
                    show_labels=show_labels,
                    color_by_cycle=False,
                    uniform_color=colors[i],
                    alpha=alpha,
                    edge_color=edge_color,
                    method_name=name
                )
                # Create legend handle for this method
                legend_handles.append(Patch(facecolor=colors[i], edgecolor=edge_color,
                                           alpha=alpha, label=name))
            else:
                # Color by cycle (each method uses same cycle colors)
                method.plot_windows(
                    ax=ax,
                    show_labels=show_labels,
                    color_by_cycle=True,
                    alpha=alpha,
                    edge_color=edge_color,
                    method_name=name
                )
                # For color_by_cycle mode, create a simple legend entry
                legend_handles.append(Patch(facecolor='gray', edgecolor=edge_color,
                                           alpha=alpha, label=name))

        ax.set_title(f'DIA Windows Overlay: {", ".join(methods_with_dia)}')
        ax.legend(handles=legend_handles, loc='best')

        # Only call tight_layout if we created the figure
        if created_fig:
            plt.tight_layout()

        return ax

    def plot_differences(self, method_names: Optional[List[str]] = None,
                        param_names: Optional[List[str]] = None,
                        figsize=(12, 8),
                        tolerance: float = 1e-6):
        """
        Plot parameter differences between methods as scatter plot with connecting lines.

        Parameters:
        -----------
        method_names : List[str], optional
            Methods to compare. If None, compares all methods.
        param_names : List[str], optional
            Specific parameters to plot. If None, plots top 20 numeric parameters with differences.
        figsize : tuple
            Figure size (default: (12, 8))
        tolerance : float
            Tolerance for detecting differences (default: 1e-6)

        Returns:
        --------
        matplotlib.figure.Figure
            The figure object with the plot
        """
        import matplotlib.pyplot as plt
        import numpy as np

        if method_names is None:
            method_names = self.list_methods()

        if len(method_names) < 2:
            print("Warning: Need at least 2 methods to compare")
            return None

        # Get differences
        result = self.find_differences(method_names=method_names, tolerance=tolerance)
        param_df = result['param_differences_df']

        if param_df.empty:
            print("No parameter differences found")
            return None

        # Select parameters to plot
        if param_names is not None:
            # Filter to requested parameters
            param_df = param_df.loc[param_df.index.intersection(param_names)]
        else:
            # Plot top 20 parameters with numeric differences
            param_df = param_df.head(20)

        if param_df.empty:
            print("No valid parameters to plot")
            return None

        # Create figure
        fig, ax = plt.subplots(figsize=figsize)

        # Prepare data for plotting
        params_to_plot = []
        for param_name, row in param_df.iterrows():
            # Check if values are numeric
            try:
                values = []
                for method_name in method_names:
                    val = row[method_name]
                    if isinstance(val, (int, float)):
                        values.append(float(val))
                    elif val is None or (isinstance(val, str) and val == ''):
                        values.append(np.nan)
                    else:
                        # Non-numeric, skip this parameter
                        values = None
                        break

                if values and not all(np.isnan(values)):
                    params_to_plot.append((param_name, values))
            except (ValueError, TypeError):
                continue

        if not params_to_plot:
            print("No numeric parameters found to plot")
            return None

        # Plot each parameter
        x_positions = range(len(method_names))
        colors = plt.cm.tab20(range(len(params_to_plot)))

        for j, (param_name, values) in enumerate(params_to_plot):
            ax.scatter(x_positions, values, color=colors[j],
                      label=param_name[:50], s=100, alpha=0.7, zorder=3)

        # Draw connecting lines between methods for each parameter
        for j, (param_name, values) in enumerate(params_to_plot):
            ax.plot(x_positions, values, color=colors[j], alpha=0.3, linewidth=1, zorder=1)

        # Customize plot
        ax.set_xticks(x_positions)
        ax.set_xticklabels(method_names, rotation=45, ha='right')
        ax.set_xlabel('Method')
        ax.set_ylabel('Parameter Value')
        ax.set_title(f'Parameter Differences: {", ".join(method_names)}')
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()

        return fig

    def compare_dia_windows(self, method_names: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Compare DIA window specifications across methods.

        Parameters:
        -----------
        method_names : List[str], optional
            Methods to compare. If None, compare all methods.

        Returns:
        --------
        pd.DataFrame
            Combined DIA windows table with method names
        """
        if method_names is None:
            method_names = self.list_methods()

        all_windows = []
        for name in method_names:
            if name in self.methods and self.methods[name].dia is not None:
                windows = self.methods[name].get_dia_windows()
                if windows is not None and len(windows) > 0:
                    windows = windows.copy()
                    windows['Method'] = name
                    all_windows.append(windows)

        if all_windows:
            return pd.concat(all_windows, ignore_index=True)
        return pd.DataFrame()

    def find_differences(self, method_names: Optional[List[str]] = None,
                        include_params: bool = True,
                        include_polarity_configs: bool = True,
                        include_dia: bool = True,
                        polarities: Optional[List[str]] = None,
                        sources: Optional[List[str]] = None,
                        tolerance: float = 1e-6) -> Dict[str, Any]:
        """
        Automatically identify differences between methods.

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
            If None, compare all available polarities.
        sources : List[str], optional
            Specific ion sources to compare ('esi', 'captivespray', 'apci', etc.).
            If None, compare all available sources.
        tolerance : float
            Tolerance for floating point comparisons (default: 1e-6)

        Returns:
        --------
        Dict[str, Any]
            Dictionary containing:
            - 'identical': bool - whether all methods are identical
            - 'param_differences_df': pd.DataFrame - global parameters that differ (wide format)
            - 'polarity_differences_df': pd.DataFrame - polarity-specific parameters that differ (wide format)
            - 'dia_differences_df': pd.DataFrame - DIA settings that differ (wide format)
            - 'summary': str - human-readable summary

        Example:
        --------
        # Compare all settings
        diffs = collection.find_differences()

        # Compare only DIA settings
        diffs = collection.find_differences(include_params=False, include_polarity_configs=False)

        # Compare only positive polarity captivespray parameters
        diffs = collection.find_differences(
            include_params=False,
            include_dia=False,
            polarities=['positive'],
            sources=['captivespray']
        )
        """
        if method_names is None:
            method_names = self.list_methods()

        if len(method_names) < 2:
            return {
                'identical': True,
                'param_differences_df': pd.DataFrame(),
                'polarity_differences_df': pd.DataFrame(),
                'dia_differences_df': pd.DataFrame(),
                'summary': 'Need at least 2 methods to compare'
            }

        result = {
            'identical': True,
            'param_differences_df': pd.DataFrame(),
            'polarity_differences_df': pd.DataFrame(),
            'dia_differences_df': pd.DataFrame(),
            'summary': ''
        }

        # Compare global MS instrument parameters
        if include_params:
            param_diffs = self._find_param_differences(method_names, tolerance,
                                                      check_polarity_configs=False)
            if param_diffs:
                result['identical'] = False
                result['param_differences_df'] = self._differences_to_df(
                    param_diffs, method_names
                )

        # Compare polarity-specific parameters
        if include_polarity_configs:
            polarity_diffs = self._find_polarity_differences(method_names, tolerance,
                                                             polarities, sources)
            if polarity_diffs:
                result['identical'] = False
                result['polarity_differences_df'] = self._differences_to_df(
                    polarity_diffs, method_names
                )

        # Compare DIA settings
        if include_dia:
            dia_diffs = self._find_dia_differences(method_names, tolerance)
            if dia_diffs:
                result['identical'] = False
                result['dia_differences_df'] = self._dia_differences_to_df(
                    dia_diffs, method_names
                )

        # Generate summary
        result['summary'] = self._generate_difference_summary(result, method_names)

        return result

    def _find_param_differences(self, method_names: List[str],
                               tolerance: float,
                               check_polarity_configs: bool = False) -> Dict[str, List[Tuple[str, Any]]]:
        """Find differences in global MS instrument parameters."""
        differences = {}

        # Get all unique parameter names across all methods
        all_param_names = set()
        for name in method_names:
            if name in self.methods:
                all_param_names.update(self.methods[name].ms.instrument_params.keys())

        # Check each parameter
        for param_name in all_param_names:
            values = {}
            for method_name in method_names:
                if method_name in self.methods:
                    value = self.methods[method_name].ms.instrument_params.get(param_name)
                    values[method_name] = value

            # Check if all values are the same
            unique_values = []
            for v in values.values():
                if isinstance(v, float):
                    # Round floats for comparison
                    comparable = round(v / tolerance) * tolerance if v is not None else None
                elif isinstance(v, list):
                    # Convert list to tuple for comparison
                    comparable = tuple(v) if v is not None else None
                else:
                    comparable = v

                if comparable not in unique_values:
                    unique_values.append(comparable)

            if len(unique_values) > 1:
                differences[param_name] = [(method_name, values[method_name])
                                          for method_name in method_names
                                          if method_name in values]

        return differences

    def _find_polarity_differences(self, method_names: List[str],
                                   tolerance: float,
                                   polarities: Optional[List[str]] = None,
                                   sources: Optional[List[str]] = None) -> Dict[str, List[Tuple[str, Any]]]:
        """Find differences in polarity-specific parameters."""
        differences = {}

        # Collect all unique polarity/source/parameter combinations
        all_configs = set()
        for method_name in method_names:
            if method_name in self.methods:
                for polarity, source_dict in self.methods[method_name].ms.polarity_configs.items():
                    # Filter by specified polarities
                    if polarities is not None and polarity not in polarities:
                        continue

                    for source, params in source_dict.items():
                        # Filter by specified sources
                        if sources is not None and source not in sources:
                            continue

                        for param_name in params.keys():
                            all_configs.add((polarity, source, param_name))

        # Check each configuration
        for polarity, source, param_name in all_configs:
            key = f"{polarity}_{source}_{param_name}"

            # Get values from all methods
            values = {}
            for method_name in method_names:
                if method_name in self.methods:
                    value = self.methods[method_name].get_param(
                        param_name, polarity=polarity, source=source
                    )
                    values[method_name] = value

            # Check if different
            unique_values = []
            for v in values.values():
                if isinstance(v, float):
                    comparable = round(v / tolerance) * tolerance if v is not None else None
                elif isinstance(v, list):
                    comparable = tuple(v) if v is not None else None
                else:
                    comparable = v

                if comparable not in unique_values:
                    unique_values.append(comparable)

            if len(unique_values) > 1:
                differences[key] = [(m, values[m]) for m in method_names if m in values]

        return differences

    def _find_dia_differences(self, method_names: List[str],
                             tolerance: float) -> Dict[str, Any]:
        """Find differences in DIA settings."""
        differences = {}

        # Check if all methods have DIA
        has_dia = {name: (name in self.methods and self.methods[name].dia is not None)
                   for name in method_names}

        if not all(has_dia.values()):
            differences['has_dia'] = has_dia
            return differences

        # Compare number of windows
        window_counts = {}
        for name in method_names:
            if name in self.methods and self.methods[name].dia is not None:
                window_counts[name] = len(self.methods[name].dia.windows)

        if len(set(window_counts.values())) > 1:
            differences['window_count'] = window_counts

        # Compare global settings
        global_params = ['OneOverK0LowerLimit', 'OneOverK0UpperLimit', 'SchemaType']
        for param in global_params:
            values = {}
            for name in method_names:
                if name in self.methods and self.methods[name].dia is not None:
                    values[name] = self.methods[name].dia.global_info.get(param)

            unique_values = set(values.values())
            if len(unique_values) > 1:
                differences[f'global_{param}'] = values

        # Compare window specifications (if same number of windows)
        if len(set(window_counts.values())) == 1:
            # Get first method as reference
            ref_method_name = method_names[0]
            ref_windows = self.methods[ref_method_name].dia.windows

            # Compare each window
            for idx, ref_row in ref_windows.iterrows():
                for col in ['MzStart', 'MzEnd', 'OneOverK0Start', 'OneOverK0End',
                           'CollisionEnergy', 'CycleId']:
                    values = {ref_method_name: ref_row[col]}

                    for name in method_names[1:]:
                        if name in self.methods and self.methods[name].dia is not None:
                            other_windows = self.methods[name].dia.windows
                            if idx < len(other_windows):
                                values[name] = other_windows.iloc[idx][col]

                    # Check if different
                    unique_values = []
                    for v in values.values():
                        if isinstance(v, (float, int)):
                            comparable = round(float(v) / tolerance) * tolerance if v is not None else None
                        elif isinstance(v, list):
                            comparable = tuple(v) if v is not None else None
                        else:
                            comparable = v

                        if comparable not in unique_values:
                            unique_values.append(comparable)

                    if len(unique_values) > 1:
                        key = f'window_{idx}_{col}'
                        differences[key] = values

        return differences

    def _differences_to_df(self, differences: Dict[str, List[Tuple[str, Any]]],
                          method_names: List[str]) -> pd.DataFrame:
        """
        Convert parameter differences dictionary to wide-format DataFrame.

        Parameters:
        -----------
        differences : Dict[str, List[Tuple[str, Any]]]
            Dictionary mapping parameter names to list of (method_name, value) tuples
        method_names : List[str]
            List of method names to include as columns

        Returns:
        --------
        pd.DataFrame
            Wide-format DataFrame with parameters as rows and methods as columns
        """
        if not differences:
            return pd.DataFrame()

        # Build the DataFrame row by row
        rows = []
        for param_name, values_list in differences.items():
            row = {'Parameter': param_name}

            # Convert list of tuples to dict
            values_dict = dict(values_list)

            # Add each method's value
            for method_name in method_names:
                value = values_dict.get(method_name)
                # Convert tuples back to lists for display
                if isinstance(value, tuple):
                    value = list(value)
                row[method_name] = value

            rows.append(row)

        df = pd.DataFrame(rows)

        # Set Parameter as index for cleaner display
        if len(df) > 0:
            df = df.set_index('Parameter')

        return df

    def _dia_differences_to_df(self, dia_differences: Dict[str, Any],
                               method_names: List[str]) -> pd.DataFrame:
        """
        Convert DIA differences dictionary to wide-format DataFrame.

        Parameters:
        -----------
        dia_differences : Dict[str, Any]
            Dictionary mapping setting names to values (can be dicts or other types)
        method_names : List[str]
            List of method names to include as columns

        Returns:
        --------
        pd.DataFrame
            Wide-format DataFrame with DIA settings as rows and methods as columns
        """
        if not dia_differences:
            return pd.DataFrame()

        rows = []
        for setting_name, values in dia_differences.items():
            row = {'Setting': setting_name}

            if isinstance(values, dict):
                # Values are already in {method_name: value} format
                for method_name in method_names:
                    value = values.get(method_name)
                    # Convert tuples back to lists for display
                    if isinstance(value, tuple):
                        value = list(value)
                    row[method_name] = value
            else:
                # Single value applies to all (e.g., structural differences)
                for method_name in method_names:
                    row[method_name] = values

            rows.append(row)

        df = pd.DataFrame(rows)

        # Set Setting as index for cleaner display
        if len(df) > 0:
            df = df.set_index('Setting')

        return df

    def _generate_difference_summary(self, result: Dict[str, Any],
                                    method_names: List[str]) -> str:
        """Generate human-readable summary of differences."""
        lines = []
        lines.append("=" * 80)
        lines.append(f"METHOD COMPARISON: {', '.join(method_names)}")
        lines.append("=" * 80)

        if result['identical']:
            lines.append("\n✓ All methods are identical")
            return '\n'.join(lines)

        lines.append("\n✗ Methods have differences:")

        # Parameter differences
        if not result['param_differences_df'].empty:
            param_df = result['param_differences_df']
            lines.append(f"\n  Global MS Instrument Parameters: {len(param_df)} difference(s)")
            lines.append("  " + "-" * 76)

            # Show first 10 differences
            for param_name, row in list(param_df.iterrows())[:10]:
                lines.append(f"    {param_name}:")
                for method_name in row.index:
                    lines.append(f"      {method_name}: {row[method_name]}")

            if len(param_df) > 10:
                lines.append(f"    ... and {len(param_df) - 10} more")

        # Polarity config differences
        if not result['polarity_differences_df'].empty:
            polarity_df = result['polarity_differences_df']
            lines.append(f"\n  Polarity-Specific Parameters: {len(polarity_df)} difference(s)")
            lines.append("  " + "-" * 76)

            # Show first 10 differences
            for param_name, row in list(polarity_df.iterrows())[:10]:
                lines.append(f"    {param_name}:")
                for method_name in row.index:
                    lines.append(f"      {method_name}: {row[method_name]}")

            if len(polarity_df) > 10:
                lines.append(f"    ... and {len(polarity_df) - 10} more")

        # DIA differences
        if not result['dia_differences_df'].empty:
            dia_df = result['dia_differences_df']
            lines.append(f"\n  DIA Settings: {len(dia_df)} difference(s)")
            lines.append("  " + "-" * 76)

            for setting_name, row in list(dia_df.iterrows())[:10]:
                lines.append(f"    {setting_name}:")
                for method_name in row.index:
                    lines.append(f"      {method_name}: {row[method_name]}")

            if len(dia_df) > 10:
                lines.append(f"    ... and {len(dia_df) - 10} more")

        lines.append("\n" + "=" * 80)
        return '\n'.join(lines)

    def save(self, filepath: str):
        """
        Save collection to file, auto-detecting format from extension.

        Supported formats:
        - .pkl, .pickle: Pickle format (preserves full BrukerMethod objects)
        - .json: JSON format (exports data only, not BrukerMethod objects)

        Parameters:
        -----------
        filepath : str
            Output file path

        Raises:
        -------
        ValueError
            If file format is not recognized
        """
        path = Path(filepath)
        suffix = path.suffix.lower()

        if suffix in ['.pkl', '.pickle']:
            self.save_pickle(filepath)
        elif suffix == '.json':
            self.save_json(filepath)
        else:
            raise ValueError(
                f"Unrecognized file format: {suffix}. "
                f"Supported: .pkl, .pickle, .json"
            )

    def save_pickle(self, filepath: str):
        """
        Save collection to pickle file (exports data only, not BrukerMethod objects).

        Note: BrukerMethod objects contain XML trees and other unpicklable objects.
        This method exports the data dictionaries instead. To load as full
        BrukerMethod objects, re-parse from original .m directories.

        Parameters:
        -----------
        filepath : str
            Output pickle file path
        """
        # Export as data dictionaries instead of full objects
        data = {}
        for name, method in self.methods.items():
            data[name] = method.to_dict()

        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'wb') as f:
            pickle.dump(data, f)
        print(f"Saved {len(self.methods)} methods to {filepath} (data only)")

    def load(self, filepath: str):
        """
        Load collection from file, auto-detecting format from extension.

        Supported formats:
        - .pkl, .pickle: Pickle format
        - .json: JSON format (loads data as dictionaries, not BrukerMethod objects)

        Parameters:
        -----------
        filepath : str
            Input file path

        Raises:
        -------
        ValueError
            If file format is not recognized
        """
        path = Path(filepath)
        suffix = path.suffix.lower()

        if suffix in ['.pkl', '.pickle']:
            self.load_pickle(filepath)
        elif suffix == '.json':
            self.load_json(filepath)
        else:
            raise ValueError(
                f"Unrecognized file format: {suffix}. "
                f"Supported: .pkl, .pickle, .json"
            )

    def load_pickle(self, filepath: str):
        """
        Load collection from pickle file.

        Note: Pickle files contain data dictionaries, not BrukerMethod objects.
        To work with actual BrukerMethod objects, re-parse from original
        .m directories using add_method() or add_methods_from_folder().

        Parameters:
        -----------
        filepath : str
            Input pickle file path
        """
        with open(filepath, 'rb') as f:
            data = pickle.load(f)

        self.methods = {}
        for name, method_data in data.items():
            # Create a pseudo-BrukerMethod object with the data
            class MethodData:
                pass

            method_obj = MethodData()
            method_obj.data = method_data

            # Add to_dict method for compatibility
            method_obj.to_dict = lambda d=method_data: d  # type: ignore

            self.methods[name] = method_obj  # type: ignore

        print(f"Loaded {len(self.methods)} methods from {filepath} (data only)")
        print("Note: Loaded as data dictionaries, not BrukerMethod objects.")

    def save_json(self, filepath: str):
        """
        Save collection to JSON file (exports data only, not BrukerMethod objects).

        Parameters:
        -----------
        filepath : str
            Output JSON file path
        """
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        data = {}
        for name, method in self.methods.items():
            data[name] = method.to_dict()

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"Saved {len(self.methods)} methods to {filepath}")

    def load_json(self, filepath: str):
        """
        Load collection from JSON file.

        Note: This loads method data as dictionaries, not BrukerMethod objects.
        To work with actual BrukerMethod objects, use pickle format or
        re-parse from original .m directories.

        Parameters:
        -----------
        filepath : str
            Input JSON file path
        """
        with open(filepath, 'r') as f:
            data = json.load(f)

        self.methods = {}
        for name, method_data in data.items():
            # Create a pseudo-BrukerMethod object with the data
            class MethodData:
                pass

            method_obj = MethodData()
            method_obj.data = method_data

            # Add to_dict method for compatibility
            method_obj.to_dict = lambda: method_data  # type: ignore

            self.methods[name] = method_obj  # type: ignore

        print(f"Loaded {len(self.methods)} methods from {filepath} (data only)")
        print("Note: Loaded as data dictionaries, not BrukerMethod objects.")

    def __len__(self) -> int:
        """Return number of methods in collection."""
        return len(self.methods)

    def __repr__(self) -> str:
        """String representation of collection."""
        return f"MSMethodCollection(n_methods={len(self.methods)})"

    def __getitem__(self, name: str) -> BrukerMethod:
        """Allow dictionary-style access to methods."""
        return self.methods[name]


# Usage example
if __name__ == "__main__":
    import sys

    # Create collection
    collection = MSMethodCollection()

    # Add methods from folder
    if len(sys.argv) > 1:
        folder_path = sys.argv[1]
    else:
        folder_path = "/Users/eileen.wang/Desktop/diann/SampleData/methods/MS"

    print("Loading methods from folder...")
    collection.add_methods_from_folder(folder_path)

    print(f"\nLoaded {len(collection)} methods")
    print(f"Methods: {', '.join(collection.list_methods())}")

    # Get summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(collection.summary_df().to_string())

    # Compare specific parameters
    print("\n" + "=" * 80)
    print("PARAMETER COMPARISON")
    print("=" * 80)
    params_to_compare = [
        'Collision_GasSupply_Set',
        'Digitizer_SampleIntervall',
        'TOF_DetectorTofSetValue'
    ]
    print(collection.compare_parameters(params_to_compare).to_string())

    # Find differences automatically
    print("\n" + "=" * 80)
    print("AUTOMATIC DIFFERENCE DETECTION")
    print("=" * 80)
    differences = collection.find_differences()
    print(differences['summary'])

    # Save collection
    print("\n" + "=" * 80)
    print("SAVING")
    print("=" * 80)
    collection.save('/tmp/ms_methods.pkl')
    collection.save('/tmp/ms_methods.json')

    # Load collection
    print("\n" + "=" * 80)
    print("LOADING")
    print("=" * 80)
    loaded = MSMethodCollection.from_file('/tmp/ms_methods.pkl')
    print(f"Loaded {len(loaded)} methods")
