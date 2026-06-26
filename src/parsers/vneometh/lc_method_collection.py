from logging import warning
import textwrap

import pandas as pd
import pickle
import h5py
import json
from pathlib import Path
from typing import Dict, List, Optional, Union
import numpy as np

from ..search.search_collection import SearchCollection
from .vneo_method import VNeoMethod
import zipfile
import tempfile
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import copy
import anndata as ad

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


class VNeoMethodCollection:
    """Collection of LC methods with storage and comparison capabilities."""

    def __init__(self, column_specs: Optional[str] = "columns.yaml"):
        """Initialize empty method collection."""
        self.methods: Dict[str, VNeoMethod] = {}
        self.adjusted_methods: Dict[str, Dict] = {}
        self.column_specs = column_specs

    @classmethod
    def from_file(cls, filepath: str) -> 'VNeoMethodCollection':
        """
        Create a new collection from a saved file.

        Parameters:
        -----------
        filepath : str
            Path to saved collection file (.pkl, .h5, .json)

        Returns:
        --------
        VNeoMethodCollection
            New collection loaded from file

        Example:
        --------
        collection = VNeoMethodCollection.from_file('methods.pkl')
        """
        collection = cls()
        collection.load(filepath)
        return collection

    def add_method(self, name: str, method: Union[str, VNeoMethod], overwrite: bool = False):
        """
        Add a method to the collection.

        Parameters:
        -----------
        name : str
            Identifier for the method
        method : str or VNeoMethod
            Path to .meth file or VNeoMethod object
        overwrite : bool
            If True, overwrite existing method with same name.
            If False, raise error if method already exists.
        """
        if name in self.methods and not overwrite:
            raise ValueError(
                f"Method '{name}' already exists in collection. "
                f"Use overwrite=True to replace it or remove_method() first."
            )

        if isinstance(method, str):
            method = VNeoMethod(method)
        self.methods[name] = method

    def add_methods_from_paths(self, method_paths: Dict[str, str], overwrite: bool = False):
        """
        Add multiple methods from file paths.

        Parameters:
        -----------
        method_paths : Dict[str, str]
            Dictionary mapping method names to .meth file paths
        overwrite : bool
            If True, overwrite existing methods with same names.
            If False, raise error if any method already exists.
        """
        for name, path in method_paths.items():
            self.add_method(name, path, overwrite=overwrite)

    def add_methods_from_folder(self, folder_path: str, overwrite: bool = False):
        """
        Add multiple methods from a folder or zip file.

        Can accept:
        - A folder containing .meth files and/or .zip files
        - A zip file directly (will extract all methods inside)

        For .zip files containing multiple methods:
        - Each method is loaded with its own name

        Parameters:
        -----------
        folder_path : str
            Path to folder containing .meth files or .zip files, OR
            Path to a .zip file containing multiple .meth files
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
                    # Find all .meth files in the zip
                    meth_in_zip = [name for name in zf.namelist()
                                  if name.endswith('.meth') and not name.startswith('__MACOSX')]

                    if len(meth_in_zip) == 0:
                        print(f"Warning: No .meth files found in {path.name}")
                        return

                    # Extract to temp directory
                    temp_dir = tempfile.mkdtemp(prefix='lc_methods_')
                    try:
                        zf.extractall(temp_dir)
                        # Add each method found in the zip
                        for meth_name in meth_in_zip:
                            # Get clean name (remove path components)
                            clean_name = Path(meth_name).stem
                            full_path = Path(temp_dir) / meth_name

                            if full_path.exists():
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

        # Find .meth files directly in folder
        meth_files = {f.stem: str(f) for f in folder.glob("*.meth")}
        all_methods.update(meth_files)

        # Find .zip files and extract methods from inside them
        for zip_file in folder.glob("*.zip"):
            try:
                with zipfile.ZipFile(zip_file, 'r') as zf:
                    # Find all .meth files in the zip
                    meth_in_zip = [name for name in zf.namelist()
                                  if name.endswith('.meth') and not name.startswith('__MACOSX')]

                    if len(meth_in_zip) == 0:
                        print(f"Warning: No .meth files found in {zip_file.name}")
                        continue

                    # Extract to temp directory
                    temp_dir = tempfile.mkdtemp(prefix='lc_methods_')
                    try:
                        zf.extractall(temp_dir)

                        # Add each method found in the zip
                        for meth_name in meth_in_zip:
                            # Get clean name (remove path components)
                            clean_name = Path(meth_name).stem
                            full_path = Path(temp_dir) / meth_name

                            if full_path.exists():
                                # If this zip only has one method, use zip name
                                if len(meth_in_zip) == 1:
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
        
    def get_method(self, name: str) -> Optional[VNeoMethod]:
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
            Summary with method name, runtime, gradient info
        """
        summary_data = []
        for name, method in self.methods.items():
            summary_data.append({
                'Method': name,
                'Runtime [min]': method.runtime,
                'Gradient Steps': len(method.gradient),
                'Start %B': method.gradient.iloc[0].get('Neo.PumpModule.Pump.%B.Value [%]', 'N/A'),
                'End %B': method.gradient.iloc[-1].get('Neo.PumpModule.Pump.%B.Value [%]', 'N/A'),
                'Flow Rate [µl/min]': method.gradient.iloc[0].get('Neo.PumpModule.Pump.Flow.Nominal [µl/min]', 'N/A')
            })
        return pd.DataFrame(summary_data)

    def compare_setup(self, method_names: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Compare all method setup parameters across methods.

        Includes runtime and all method parameters (params dict).
        Returns a wide-format DataFrame with parameters as rows and methods as columns.

        Parameters:
        -----------
        method_names : List[str], optional
            Methods to compare. If None, compare all methods.

        Returns:
        --------
        pd.DataFrame
            Wide-format DataFrame with parameters as index and methods as columns

        Example:
        --------
        collection = VNeoMethodCollection()
        collection.add_method('method1', 'path/to/method1.meth')
        collection.add_method('method2', 'path/to/method2.meth')

        # Compare all parameters
        comparison = collection.compare_setup()
        print(comparison)

        # Compare specific methods
        comparison = collection.compare_setup(['method1', 'method2'])
        """
        if method_names is None:
            method_names = self.list_methods()

        if not method_names:
            return pd.DataFrame()

        # Collect all unique parameter keys across all methods
        all_param_keys = set()
        for name in method_names:
            if name in self.methods:
                all_param_keys.update(self.methods[name].params.keys())

        # Sort parameter keys for consistent ordering
        param_keys = ['Runtime [min]'] + sorted(all_param_keys)

        # Build comparison data
        data = {}
        for name in method_names:
            if name in self.methods:
                method = self.methods[name]
                column_data = {}

                # Add runtime
                column_data['Runtime [min]'] = method.runtime

                # Add all params
                for key in all_param_keys:
                    column_data[key] = method.params.get(key, None)

                data[name] = column_data

        # Create DataFrame
        df = pd.DataFrame(data, index=param_keys)

        return df

    def compare_gradients(self, method_names: Optional[List[str]] = None, columns: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Compare gradient profiles across methods (long format).

        Parameters:
        -----------
        method_names : List[str], optional
            Methods to compare. If None, compare all methods.

        Returns:
        --------
        pd.DataFrame
            Combined gradient table with method names in long format
        """
        if method_names is None:
            method_names = self.list_methods()

        # ...existing code...
        if method_names is None:
            method_names = self.list_methods()

        if not method_names:
            return {}

        # Identify columns to compare
        first_method = self.methods[method_names[0]]

        # Find time column (case-insensitive)
        time_col = None
        for col in first_method.gradient.columns:
            if 'time' in col.lower():
                time_col = col
                break

        if time_col is None:
            print("Warning: Could not find time column")
            return {}

        if columns is None:
            # Use all numeric gradient columns except time
            columns = [col for col in first_method.gradient.columns
                      if col != time_col and
                      pd.api.types.is_numeric_dtype(first_method.gradient[col])]

        # Build comparison for each column
        comparisons = {}
        for col in columns:
            data = {}
            for name in method_names:
                if name in self.methods:
                    method = self.methods[name]
                    # Find time column in this method (may vary)
                    method_time_col = None
                    for c in method.gradient.columns:
                        if 'time' in c.lower():
                            method_time_col = c
                            break

                    if method_time_col and col in method.gradient.columns:
                        data[name] = pd.Series(
                            method.gradient[col].values,
                            index=method.gradient[method_time_col].values
                        )

            if data:
                df = pd.DataFrame(data)
                df.index.name = time_col
                comparisons[col] = df

        return comparisons

    def plot_gradients(self, 
                       method_names: Optional[Union[str, List[str]]] = None,
                       sample_var: Optional[pd.DataFrame] = None,
                       x_cols: Optional[Union[None, str, List[str]]] = None,
                       y_cols: Optional[Union[None, str, List[str]]] = None,
                       twin_axes: bool = False,
                       markers: bool = False,
                       figsize=(12, 6),
                       ax=None,
                       x_shift=0):
        """
        Plot gradient profiles from multiple methods overlaid.

        Parameters:
        -----------
        method_names : List[str], optional
            Methods to plot. If None, plots all methods.
        x_col : str or List[str], optional
            Column(s) to use for x-axis. If None, uses time column (case-insensitive search).
            Can be a single column name or list of column names.
            Examples: 'Neo.PumpModule.Pump.Time [min]' or
                     ['Neo.PumpModule.Pump.Time [min]', 'Neo.PumpModule.Pump.%B.Value [%]']
        y_cols : str or List[str], optional
            Column(s) to plot on y-axis. If None, plots %B by default.
            Can be a single column name or list of column names.
            Examples: 'Neo.PumpModule.Pump.%B.Value [%]' or
                     ['Neo.PumpModule.Pump.%B.Value [%]', 'Neo.PumpModule.Pump.Flow.Nominal [µl/min]']
        twin_axes : bool
            If True and multiple y_cols are provided, creates separate y-axes for each column.
            First column uses left y-axis, second uses right y-axis (twinx).
            Useful when y columns have different scales. (default: False)
        markers : bool
            If True, adds small circular markers with white outlines at each data point.
            Useful for visualizing gradient steps. (default: False)
        figsize : tuple
            Figure size (default: (12, 6)), only used if ax is None
        ax : matplotlib.axes.Axes, optional
            Axes to plot on. If None, creates a new figure.

        Returns:
        --------
        matplotlib.axes.Axes or tuple
            If twin_axes=False: returns the main axis
            If twin_axes=True: returns tuple of axes
        Examples:
        ---------
        # Plot time vs %B (default)
        collection.plot_gradients()

        # Plot time vs flow rate
        collection.plot_gradients(y_cols='Neo.PumpModule.Pump.Flow.Nominal [µl/min]')

        # Plot time vs multiple columns
        collection.plot_gradients(y_cols=['Neo.PumpModule.Pump.%B.Value [%]',
                                          'Neo.PumpModule.Pump.Flow.Nominal [µl/min]'])

        # Multiple x columns (creates separate plots for each x-y combination)
        collection.plot_gradients(x_col=['Neo.PumpModule.Pump.Time [min]',
                                        'Neo.PumpModule.Pump.%B.Value [%]'],
                                 y_cols='Neo.PumpModule.Pump.Flow.Nominal [µl/min]')

        # Multiple x and y columns (pairs them: x[0] with y[0], x[1] with y[1])
        collection.plot_gradients(x_col=['Neo.PumpModule.Pump.Time [min]',
                                        'Neo.PumpModule.Pump.%B.Value [%]'],
                                 y_cols=['Neo.PumpModule.Pump.Flow.Nominal [µl/min]',
                                        'Neo.PumpModule.Pump.Pressure [bar]'])

        # Custom x and y axes
        collection.plot_gradients(x_col='Neo.PumpModule.Pump.%B.Value [%]',
                                 y_cols='Neo.PumpModule.Pump.Flow.Nominal [µl/min]')

        # Plot with twin y-axes (different scales)
        collection.plot_gradients(y_cols=['Neo.PumpModule.Pump.%B.Value [%]',
                                          'Neo.PumpModule.Pump.Flow.Nominal [µl/min]'],
                                 twin_axes=True)

        # Plot with markers at data points
        collection.plot_gradients(markers=True)
        """
        # if no methods and no sample defined, simply plot all unadjusted methods

        if method_names is None:
            if sample_var is None:
                method_names = self.list_methods()
                first_method = self.methods[method_names[0]]
            else:
                # if selecting by sample, need to use an adjusted method to check in case using any of the additional columns there
                method_names = sample_var['lc meth'].unique().tolist()
                if 'File.Name' not in sample_var.columns:
                    sample_col = 'sample_name'
                else:
                    sample_col = 'File.Name'
                first_row = sample_var.reset_index(drop=True).iloc[0]
                first_sample = first_row[sample_col]
                first_method_name = first_row['lc meth']
                first_method = self.adjusted_methods[first_method_name][first_sample]

        else:
            if isinstance(method_names, str):
                method_names = [method_names]
            
            first_method = self.methods[method_names[0]]

        methods = {}
        if sample_var is None:
            for m in method_names:
                methods[m] = self.methods[m]
        else:
            if 'File.Name' not in sample_var.columns:
                sample_col = 'sample_name'
            else:
                sample_col = 'File.Name'
            for m in method_names:
                temp = sample_var[sample_var['lc meth'] == m]
                for s in temp[sample_col]:
                    methods[f'{m} + {s}'] = self.adjusted_methods[m][s]

        # Handle column specifications - convert to dictionary format for better organization
        if x_cols is None:
            x_cols = ['time [min]']
        elif isinstance(x_cols, str):
            x_cols = [x_cols]

        if y_cols is None:
            y_cols = ['Neo.PumpModule.Pump.Flow.Nominal [µl/min]', 'Neo.PumpModule.Pump.%B.Value [%]']
        elif isinstance(y_cols, str):
            y_cols = [y_cols]

        # Create column specifications dictionary
        if len(x_cols) > 1 and len(y_cols) > 1 and len(x_cols) == len(y_cols):
            # Pair x and y columns when equal lengths
            column_specs = {f"plot_{i+1}": {"x": x_col, "y": y_col} 
                           for i, (x_col, y_col) in enumerate(zip(x_cols, y_cols))}
        else:
            # Create all combinations of x and y
            column_specs = {f"plot_{i+1}": {"x": x_col, "y": y_col} 
                           for i, (x_col, y_col) in enumerate(
                               (x_col, y_col) for x_col in x_cols for y_col in y_cols
                           )}
        
        # Extract column pairs for backwards compatibility
        column_pairs = [(spec["x"], spec["y"]) for spec in column_specs.values()]

        # Validate x columns
        for x in x_cols:
            print(first_method.gradient.columns)
            if x not in first_method.gradient.columns:
                print(f"Warning: X column '{x}' not found in gradient data.")
                return None

        # Validate y columns
        for y in y_cols:
            if y not in first_method.gradient.columns:
                print(f"Warning: Y column '{y}' not found in gradient data.")
                return None

        # Create figure if ax not provided
        created_fig = ax is None
        if ax is None:
            fig, ax = plt.subplots(figsize=figsize)

        # Create twin axes if requested and multiple y columns
        axes = [ax]
        if twin_axes and len(y_cols) > 1:
            for _ in range(len(y_cols) - 1):
                axes.append(ax.twinx())

        # Plot each method
        # Ensure colors array matches the number of methods
        color_count = max(len(methods), 1)
        colors = plt.cm.tab10(range(color_count))
        linestyles = ['-', '--', '-.', ':']

        legend_lines = []
        legend_labels = []
        # When both x and y are specified, show x-y pair combinations in legend
        if len(x_cols) > 0 and len(y_cols) > 0:
            # Create legend entries for method-color combinations
            for i, method_name in enumerate(methods.keys()):
                line = Line2D([0], [0], color=colors[i], linestyle='-', linewidth=2)
                legend_lines.append(line)
                wrapped_method = '\n'.join(textwrap.wrap(str(method_name), width=30))
                legend_labels.append(f"{wrapped_method}")
            
            # Create legend entries for x-y pair combinations using column_specs dictionary
            for pair_idx, (plot_name, spec) in enumerate(column_specs.items()):
                line = Line2D([0], [0], color='black', linestyle=linestyles[pair_idx % len(linestyles)], linewidth=2)
                legend_lines.append(line)
                
                # Create readable x-y pair label
                x_col, y_col = spec["x"], spec["y"]
                x_short = x_col.split('.')[-1] if '.' in x_col else x_col
                y_short = y_col.split('.')[-1] if '.' in y_col else y_col
                pair_label = f"{x_short} vs {y_short}"
                wrapped_label = '\n'.join(textwrap.wrap(pair_label, width=30))
                legend_labels.append(f"{wrapped_label}")
        else:
            # Fallback to original legend for simple cases
            for i, method_name in enumerate(methods.keys()):
                line = Line2D([0], [0], color=colors[i], linestyle='-', linewidth=2)
                legend_lines.append(line)
                wrapped_method = '\n'.join(textwrap.wrap(str(method_name), width=30))
                legend_labels.append(f"{wrapped_method}")
            for pair_idx, y_col in enumerate(y_cols):
                line = Line2D([0], [0], color='black', linestyle=linestyles[pair_idx % len(linestyles)], linewidth=2)
                legend_lines.append(line)
                wrapped_label = '\n'.join(textwrap.wrap(str(y_col), width=30))
                legend_labels.append(f"Column: {wrapped_label}")

        for i, (name, method) in enumerate(methods.items()):
            for pair_idx, (x_col, y_col) in enumerate(column_pairs):
                if x_col not in method.gradient.columns:
                    print(f"Warning: x_col '{x_col}' not found in method '{name}', skipping")
                    continue
                if y_col not in method.gradient.columns:
                    print(f"Warning: y_col '{y_col}' not found in method '{name}', skipping")
                    continue
                y_idx = y_cols.index(y_col) if y_col in y_cols else 0
                if twin_axes and len(y_cols) > 1:
                    current_ax = axes[min(y_idx, len(axes) - 1)]
                else:
                    current_ax = ax
                plot_kwargs = {
                    'color': colors[i],
                    'linewidth': 2,
                    'alpha': 0.8,
                    'linestyle': linestyles[pair_idx % len(linestyles)]
                }
                if markers:
                    plot_kwargs.update({
                        'marker': 'o',
                        'markersize': 5,
                        'markeredgecolor': 'white',
                        'markeredgewidth': 0.8
                    })
                current_ax.plot(method.gradient[x_col] + x_shift,
                               method.gradient[y_col],
                               **plot_kwargs)

        # Set axis labels
        if len(x_cols) == 1:
            xlabel = x_cols[0]
        elif all('time' in col.lower() for col in x_cols):
            # If all x columns contain 'time', use simple time label
            xlabel = "time [min]"
        else:
            xlabel = "X Value"
        ax.set_xlabel(xlabel)

        # Set y-axis labels
        if twin_axes and len(y_cols) > 1:
            # Set labels for each axis, color-coded and offset
            for y_idx, y_col in enumerate(y_cols):
                if y_idx < len(axes):
                    ylabel = y_col
                    axes[y_idx].set_ylabel(ylabel, color=colors[y_idx % len(colors)])
                    # Offset label position to avoid overlap
                    if y_idx == 0:
                        axes[y_idx].yaxis.set_label_coords(-0.13, 0.5)
                    else:
                        axes[y_idx].yaxis.set_label_coords(1.13, 0.5)
        if len(y_cols) == 1:
            ylabel = y_cols[0]
            ax.set_ylabel(ylabel)
        else:
            ax.set_ylabel('Value')
        # Show only one legend with both sets of entries
        ax.legend(
            legend_lines,
            legend_labels,
            loc='center left',
            bbox_to_anchor=(1.1, 0.5),
            fancybox=True,
            frameon=True,
            borderaxespad=0,
            ncol=1,
            handletextpad=0.5
        )

        # Create informative title
        # if len(x_cols) == 1 and len(y_cols) == 1:
        #     title = f'Gradient Comparison: {", ".join(method_names)}'
        # else:
        #     x_desc = f"{len(x_cols)} X-columns" if len(x_cols) > 1 else x_cols[0].split('.')[-1]
        #     y_desc = f"{len(y_cols)} Y-columns" if len(y_cols) > 1 else y_cols[0].split('.')[-1] 
        #     title = f'Gradient Comparison ({x_desc} vs {y_desc}): {", ".join(method_names)}'
        ax.set_title('Gradient Comparison')
        ax.grid(True, alpha=0.3)

        # Only call tight_layout if we created the figure
        if created_fig:
            plt.tight_layout()

        # Return appropriate axes
        if twin_axes and len(y_cols) > 1:
            return tuple(axes)
        return ax

    def save(self, filepath: str):
        """
        Save collection to file, auto-detecting format from extension.

        Supported formats:
        - .pkl, .pickle: Pickle format
        - .h5, .hdf5: HDF5 format
        - .json: JSON format

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
        elif suffix in ['.h5', '.hdf5']:
            self.save_hdf5(filepath)
        elif suffix == '.json':
            self.save_json(filepath)
        else:
            raise ValueError(
                f"Unrecognized file format: {suffix}. "
                f"Supported: .pkl, .pickle, .h5, .hdf5, .json"
            )

    def save_pickle(self, filepath: str):
        """
        Save collection to pickle file.

        Parameters:
        -----------
        filepath : str
            Output pickle file path
        """
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'wb') as f:
            pickle.dump(self.methods, f)
        print(f"Saved {len(self.methods)} methods to {filepath}")

    def load(self, filepath: str):
        """
        Load collection from file, auto-detecting format from extension.

        Supported formats:
        - .pkl, .pickle: Pickle format
        - .h5, .hdf5: HDF5 format
        - .json: JSON format

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
        elif suffix in ['.h5', '.hdf5']:
            self.load_hdf5(filepath)
        elif suffix == '.json':
            self.load_json(filepath)
        else:
            raise ValueError(
                f"Unrecognized file format: {suffix}. "
                f"Supported: .pkl, .pickle, .h5, .hdf5, .json"
            )

    def load_pickle(self, filepath: str):
        """
        Load collection from pickle file.

        Parameters:
        -----------
        filepath : str
            Input pickle file path
        """
        with open(filepath, 'rb') as f:
            self.methods = pickle.load(f)
        print(f"Loaded {len(self.methods)} methods from {filepath}")

    def save_hdf5(self, filepath: str):
        """
        Save collection to HDF5 file.

        Parameters:
        -----------
        filepath : str
            Output HDF5 file path
        """
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        with h5py.File(filepath, 'w') as f:
            for name, method in self.methods.items():
                grp = f.create_group(name)

                # Save scalar attributes
                grp.attrs['runtime'] = method.runtime
                grp.attrs['params'] = json.dumps(method.params)

                # Save gradient DataFrame
                gradient_records = method.gradient.to_records(index=False)
                grp.create_dataset('gradient', data=gradient_records)

                # Save equilibration DataFrame
                equil_records = method.equil.to_records(index=False)
                grp.create_dataset('equil', data=equil_records)

        print(f"Saved {len(self.methods)} methods to {filepath}")

    def load_hdf5(self, filepath: str):
        """
        Load collection from HDF5 file.

        Note: This loads method data as dictionaries, not VNeoMethod objects.
        To reconstruct VNeoMethod objects, use load_hdf5_as_objects().

        Parameters:
        -----------
        filepath : str
            Input HDF5 file path
        """
        self.methods = {}

        with h5py.File(filepath, 'r') as f:
            for name in f.keys():
                grp = f[name]

                # Create a pseudo-VNeoMethod object with the data
                class MethodData:
                    pass

                method_obj = MethodData()
                method_obj.runtime = grp.attrs['runtime']
                method_obj.params = json.loads(grp.attrs['params'])
                method_obj.gradient = pd.DataFrame(grp['gradient'][:])
                method_obj.equil = pd.DataFrame(grp['equil'][:])

                self.methods[name] = method_obj  # type: ignore

        print(f"Loaded {len(self.methods)} methods from {filepath}")

    def save_json(self, filepath: str):
        """
        Save collection to JSON file (human-readable).

        Parameters:
        -----------
        filepath : str
            Output JSON file path
        """
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)

        data = {}
        for name, method in self.methods.items():
            data[name] = {
                'runtime': method.runtime,
                'params': method.params,
                'gradient': method.gradient.to_dict('records'),
                'equil': method.equil.to_dict('records')
            }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"Saved {len(self.methods)} methods to {filepath}")

    def load_json(self, filepath: str):
        """
        Load collection from JSON file.

        Note: This loads method data as dictionaries, not VNeoMethod objects.

        Parameters:
        -----------
        filepath : str
            Input JSON file path
        """
        with open(filepath, 'r') as f:
            data = json.load(f)

        self.methods = {}
        for name, method_data in data.items():
            # Create a pseudo-VNeoMethod object with the data
            class MethodData:
                pass

            method_obj = MethodData()
            method_obj.runtime = method_data['runtime']
            method_obj.params = method_data['params']
            method_obj.gradient = pd.DataFrame(method_data['gradient'])
            method_obj.equil = pd.DataFrame(method_data['equil'])

            self.methods[name] = method_obj  # type: ignore

        print(f"Loaded {len(self.methods)} methods from {filepath}")

    def __len__(self) -> int:
        """Return number of methods in collection."""
        return len(self.methods)

    def __repr__(self) -> str:
        """String representation of collection."""
        return f"VNeoMethodCollection(n_methods={len(self.methods)}, adjusted_methods={len(self.adjusted_methods)})"

    def __getitem__(self, name: str) -> VNeoMethod:
        """Allow dictionary-style access to methods."""
        return self.methods[name]


    def copy(self) -> 'VNeoMethodCollection':
        """Return a deep copy of the collection."""
        return copy.deepcopy(self)
    
    def bulk_adjust_gradients(self, 
        searchcollection: SearchCollection,
        samples: Optional[list[str]] = None,
        lcmethods: Optional[list[str]] = None,
        extrapolate_points: Optional[list] = None,
        direct_only: Optional[float] = None
        ):
        """
        Adjust gradient profiles in all methods based on a search collection.

        For each method, finds the closest matching gradient profile in the search collection
        and applies adjustments to align them. This can help correct for systematic differences
        between methods and make them more comparable.

        Parameters:
        -----------
        searchcollection : SearchCollection
            Collection containing reference gradient profiles to match against
        samples : Optional[list[str]]
            List of specific samples to process
        lcmethods : Optional[list[str]]  
            List of specific LC methods to process
        extrapolate_points : list of dict, optional
            Additional gradient points to add at end. Each dict should contain:
            {'time': float, 'b_percent': float, 'flow_rate': float}
            where 'time' is the length/duration of the interval (not absolute time)
        direct_only : float, optional
            Direct injection dead volume in nL (for trap column bypass scenarios)

        Returns:
        --------
        Dict[str, pd.DataFrame]
            Dictionary mapping method names to their adjusted gradient DataFrames
        """
        not_found = []

        if 'diann' in searchcollection.search_type:
            if 'precursor' not in searchcollection.list_levels():
                warning("Precursor level not found in search collection. Cannot adjust gradients.")
            ad = searchcollection['precursor'] 
            sample_col = 'File.Name'

        elif 'spectronaut' in searchcollection.search_type:
            if 'peptide' not in searchcollection.list_levels():
                warning("Peptide level not found in search collection. Cannot adjust gradients.")
            ad = searchcollection['peptide']
            sample_col = 'sample_name'

        if samples:
            ad = ad[ad.var_names.isin(samples)]
        if lcmethods:
            ad = ad[ad.var['lc meth'].isin(lcmethods)]
        for idx, row in ad.var.iterrows(): # type: ignore
            sample_name = row[sample_col]
            lcmethod_name = row['lc meth']

            # Get RT values based on search type
            if 'spectronaut' in searchcollection.search_type:
                # For Spectronaut, use rt_start layer
                rt_values = ad[:, ad.var[sample_col] == sample_name].layers['rt_start']
            else:
                # For DIA-NN, use RT layer
                rt_values = ad[:, ad.var[sample_col] == sample_name].layers['RT']
                
            # Handle NaN values safely
            if isinstance(rt_values, (np.ndarray, pd.Series)):
                min_rt = np.nanmin(rt_values)
            else:
                min_rt = float(rt_values)

            method_obj = self.get_method(lcmethod_name)
            if method_obj is None:
                not_found.append(lcmethod_name) 
                continue

            if lcmethod_name not in self.adjusted_methods:
                self.adjusted_methods[lcmethod_name] = {}

            self.adjusted_methods[lcmethod_name][sample_name] = method_obj.adjusted_elution(
                dead_time=min_rt, 
                in_place=False,
                extrapolate_points=extrapolate_points,
                direct_only=direct_only
            )
        
        # print(f"Adjusted gradients for {len(self.adjusted_methods)} methods. Not found: {pd.Series(not_found).unique()}")


#     def plot_gradients_interact(self, 
#                        method_names: Optional[List[str]] = None,
#                        sample_var: Optional[pd.DataFrame] = None,
#                        x_cols: Optional[Union[None, str, List[str]]] = None,
#                        y_cols: Optional[Union[None, str, List[str]]] = None,
#                        twin_axes: bool = False,
#                        markers: bool = False,
#                        figsize=(12, 6),
#                        fig: Optional[go.Figure] = None,
#                        x_shift=0) -> go.Figure:
#         """
#         Plot gradient profiles from multiple methods overlaid.

#         Parameters:
#         -----------
#         method_names : List[str], optional
#             Methods to plot. If None, plots all methods.
#         x_col : str or List[str], optional
#             Column(s) to use for x-axis. If None, uses time column (case-insensitive search).
#             Can be a single column name or list of column names.
#             Examples: 'Neo.PumpModule.Pump.Time [min]' or
#                      ['Neo.PumpModule.Pump.Time [min]', 'Neo.PumpModule.Pump.%B.Value [%]']
#         y_cols : str or List[str], optional
#             Column(s) to plot on y-axis. If None, plots %B by default.
#             Can be a single column name or list of column names.
#             Examples: 'Neo.PumpModule.Pump.%B.Value [%]' or
#                      ['Neo.PumpModule.Pump.%B.Value [%]', 'Neo.PumpModule.Pump.Flow.Nominal [µl/min]']
#         twin_axes : bool
#             If True and multiple y_cols are provided, creates separate y-axes for each column.
#             First column uses left y-axis, second uses right y-axis (twinx).
#             Useful when y columns have different scales. (default: False)
#         markers : bool
#             If True, adds small circular markers with white outlines at each data point.
#             Useful for visualizing gradient steps. (default: False)
#         figsize : tuple
#             Figure size (default: (12, 6)), only used if ax is None
#         ax : matplotlib.axes.Axes, optional
#             Axes to plot on. If None, creates a new figure.

#         Returns:
#         --------
#         matplotlib.axes.Axes or tuple
#             If twin_axes=False: returns the main axis
#             If twin_axes=True: returns tuple of axes
#         Examples:
#         ---------
#         # Plot time vs %B (default)
#         collection.plot_gradients()

#         # Plot time vs flow rate
#         collection.plot_gradients(y_cols='Neo.PumpModule.Pump.Flow.Nominal [µl/min]')

#         # Plot time vs multiple columns
#         collection.plot_gradients(y_cols=['Neo.PumpModule.Pump.%B.Value [%]',
#                                           'Neo.PumpModule.Pump.Flow.Nominal [µl/min]'])

#         # Multiple x columns (creates separate plots for each x-y combination)
#         collection.plot_gradients(x_col=['Neo.PumpModule.Pump.Time [min]',
#                                         'Neo.PumpModule.Pump.%B.Value [%]'],
#                                  y_cols='Neo.PumpModule.Pump.Flow.Nominal [µl/min]')

#         # Multiple x and y columns (pairs them: x[0] with y[0], x[1] with y[1])
#         collection.plot_gradients(x_col=['Neo.PumpModule.Pump.Time [min]',
#                                         'Neo.PumpModule.Pump.%B.Value [%]'],
#                                  y_cols=['Neo.PumpModule.Pump.Flow.Nominal [µl/min]',
#                                         'Neo.PumpModule.Pump.Pressure [bar]'])

#         # Custom x and y axes
#         collection.plot_gradients(x_col='Neo.PumpModule.Pump.%B.Value [%]',
#                                  y_cols='Neo.PumpModule.Pump.Flow.Nominal [µl/min]')

#         # Plot with twin y-axes (different scales)
#         collection.plot_gradients(y_cols=['Neo.PumpModule.Pump.%B.Value [%]',
#                                           'Neo.PumpModule.Pump.Flow.Nominal [µl/min]'],
#                                  twin_axes=True)

#         # Plot with markers at data points
#         collection.plot_gradients(markers=True)
#         """
#         # if no methods and no sample defined, simply plot all unadjusted methods


#         # TODO: toggle by 1. method, 2. trace type 3. sample (if adjusted) 4. combination

#         if method_names is None:
#             if sample_var is None:
#                 method_names = self.list_methods()
#                 first_method = self.methods[method_names[0]]
#             else:
#                 # if selecting by sample, need to use an adjusted method to check in case using any of the additional columns there
#                 method_names = sample_var['lc meth'].unique().tolist()
                
#                 first_row = sample_var.reset_index(drop=True).iloc[0]
#                 first_sample = first_row['File.Name']
#                 first_method_name = first_row['lc meth']
#                 first_method = self.adjusted_methods[first_method_name][first_sample]
        
#         toggle_dict = {}
#         methods = {}
#         # if no individual samples are defined, only look at the methods 
#         if sample_var is None:
#             for m in method_names:
#                 methods[m] = self.methods[m]

#         # if individual samples are defined, need to look at the adjusted methods for each sample and method combination
#         else:
#             for m in method_names:
#                 temp = sample_var[sample_var['lc meth'] == m]
#                 for s in temp['File.Name']:
#                     if m in methods.keys():
#                         methods[m][s] = self.adjusted_methods[m][s]
#                     else:
#                         methods[m] = {s: self.adjusted_methods[m][s]}

#         if x_cols is None:
#             x_cols = ['time [min]']
#         elif isinstance(x_cols, str):
#             x_cols = [x_cols]

#         if y_cols is None:
#             y_cols = ['Neo.PumpModule.Pump.Flow.Nominal [µl/min]', 'Neo.PumpModule.Pump.%B.Value [%]']
#         elif isinstance(y_cols, str):
#             y_cols = [y_cols]

#         # Validate x columns
#         for x in x_cols:
#             if x not in first_method.gradient.columns:
#                 print(f"Warning: X column '{x}' not found in gradient data.")
#                 return None

#         # Validate y columns
#         for y in y_cols:
#             if y not in first_method.gradient.columns:
#                 print(f"Warning: Y column '{y}' not found in gradient data.")
#                 return None

#         # Create figure if fig not provided
#         if fig is None:
#             if twin_axes is None:
#                 fig = go.Figure(figsize=figsize)
#             else:
#                 fig = make_subplots(specs=[[{"secondary_y": True}]])

#         # Plot each method
#         # Ensure colors array matches the number of methods
#         color_count = max(len(methods), 1)
#         colors = plt.cm.tab10(range(color_count))
#         linestyles = ['-', '--', '-.', ':']

#         legend_lines = []
#         legend_labels = []

#         col_pairs = [(x, y) for x in x_cols for y in y_cols]

#         # define line styles to be used

#         for i, (x, y) in enumerate(col_pairs):
#             line = Line2D([0], [0], color='black', linestyle=linestyles[i % len(linestyles)], linewidth=2)
#             legend_lines.append(line)
#             wrapped_label = '\n'.join(textwrap.wrap(f'{x} vs {y}', width=30))
#             legend_labels.append(f"Column: {wrapped_label}")

#         toggle_dict['method'] = {method_name: [] for method_name in methods.keys()}
#         toggle_dict['x+y'] = {f'{x}+{y}': [] for x, y in col_pairs}
#         if sample_var is not None:
#             toggle_dict['sample'] = {sample_name: [] for sample_name in sample_var['File.Name'].unique().tolist()}  


#         if sample_var is None:
#             for i, (method_name, method) in enumerate(methods.items()):
#                 for pair_idx, (x, y) in enumerate(col_pairs):
#                     if x not in method.gradient.columns:
#                         print(f"Warning: x_col '{x}' not found in method '{method_name}', skipping")
#                         continue
#                     if y not in method.gradient.columns:
#                         print(f"Warning: y_col '{y}' not found in method '{method_name}', skipping")
#                         continue
                    
#                     plot_kwargs = {
#                         'color': colors[i],
#                         'linewidth': 2,
#                         'alpha': 0.8,
#                         'linestyle': linestyles[pair_idx % len(linestyles)]
#                     }
#                     if markers:
#                         plot_kwargs.update({
#                             'marker': 'o',
#                             'markersize': 5,
#                             'markeredgecolor': 'white',
#                             'markeredgewidth': 0.8
#                         })
#                     trace_name = f'{method_name} - {x} vs {y}'

#                     fig.add_trace(go.Scatter(
#                         x=method.gradient[x] + x_shift,
#                         y=method.gradient[y],
#                         mode='lines+markers' if markers else 'lines',
#                         line=dict(color=colors[i], width=2, dash=linestyles[pair_idx % len(linestyles)]),
#                         # marker=dict(color=colors[i], size=5, line=dict(color='white', width=0.8)) if markers else None,
#                         name=trace_name,
#                     ))
#                     toggle_dict['method'][method_name].append(trace_name)
#                     toggle_dict['x+y'][f'{x}+{y}'].append(trace_name)

#         else:
#             for i, (method_name, sample_dict) in enumerate(methods.items()):
#                 for sample_name, method in sample_dict.items():
#                     for pair_idx, (x, y) in enumerate(col_pairs):
#                         if x not in method.gradient.columns:
#                             print(f"Warning: x_col '{x}' not found in method '{method_name}', skipping")
#                             continue
#                         if y not in method.gradient.columns:
#                             print(f"Warning: y_col '{y}' not found in method '{method_name}', skipping")
#                             continue
                        
#                         plot_kwargs = {
#                             'color': colors[i],
#                             'linewidth': 2,
#                             'alpha': 0.8,
#                             'linestyle': linestyles[pair_idx % len(linestyles)]
#                         }
#                         if markers:
#                             plot_kwargs.update({
#                                 'marker': 'o',
#                                 'markersize': 5,
#                                 'markeredgecolor': 'white',
#                                 'markeredgewidth': 0.8
#                             })
                            
#                         trace_name = f"{sample_name} - {method_name} - {x} vs {y}"
# s
#                         fig.add_trace(go.Scatter(
#                             x=method.gradient[x] + x_shift,
#                             y=method.gradient[y],
#                             mode='lines+markers' if markers else 'lines',
#                             # line=dict(color=colors[i], width=2, dash=linestyles[pair_idx % len(linestyles)]),
#                             # marker=dict(color=colors[i], size=5, line=dict(color='white', width=0.8)) if markers else None,
#                             name=trace_name
#                             ))

#                         toggle_dict['method'][method_name].append(trace_name)
#                         toggle_dict['x+y'][f'{x}+{y}'].append(trace_name)
#                         toggle_dict['sample'][sample_name].append(trace_name)

#         # Build correct visibility toggles for all traces
#         buttons = []
#         all_trace_names = [t.name for t in fig.data]
#         # Default: only the first group is visible, others hidden
#         default_group = None
#         for general, trace_dict in toggle_dict.items():
#             for idx, (trace_name, group_traces) in enumerate(trace_dict.items()):
#                 visible = [name in group_traces for name in all_trace_names]
#                 if default_group is None:
#                     default_group = visible
#                 buttons.append(dict(
#                     label=trace_name,
#                     method='update',
#                     args=[{'visible': visible}]
#                 ))

#         # Set initial visibility: only first group visible, others hidden
#         if default_group is not None:
#             for i, trace in enumerate(fig.data):
#                 trace.visible = default_group[i]

#         # Add buttons to the layout, move them outside the plot area
#         fig.update_layout(
#             updatemenus=[dict(
#                 type="buttons",
#                 direction="down",
#                 buttons=buttons,
#                 showactive=True,
#                 x=1.15,  # move to right of plot
#                 xanchor="left",
#                 y=1,
#                 yanchor="top"
#             )],
#             hovermode="x"
#         )

#         return fig


# Usage example
if __name__ == "__main__":
    # Create collection
    collection = VNeoMethodCollection()

    # Add methods from paths
    collection.add_methods_from_paths({
        'method1': 'path/to/method1.meth',
        'method2': 'path/to/method2.meth'
    })

    # Or add individual methods
    collection.add_method('method3', VNeoMethod('path/to/method3.meth'))

    # Get summary
    print(collection.summary_df())

    # Compare gradients
    print(collection.compare_gradients(['method1', 'method2']))

    # Save - auto-detects format from extension
    collection.save('methods.pkl')  # Saves as pickle
    collection.save('methods.h5')   # Saves as HDF5
    collection.save('methods.json') # Saves as JSON

    # Or use specific saver if preferred
    collection.save_pickle('methods.pkl')     # Python-only workflows
    collection.save_hdf5('methods.h5')        # Integration with h5ad files
    collection.save_json('methods.json')      # Human-readable, version control

    # Load from any format - auto-detects from extension
    new_collection = VNeoMethodCollection()
    new_collection.load('methods.pkl')  # Auto-detects pickle format

    # Or create collection directly from file
    loaded_collection = VNeoMethodCollection.from_file('methods.h5')

    # Or use specific loader if preferred
    another_collection = VNeoMethodCollection()
    another_collection.load_json('methods.json')

    # Access methods
    method = new_collection['method1']
    print(f"Runtime: {method.runtime}")
    print(f"Gradient:\n{method.gradient}")
