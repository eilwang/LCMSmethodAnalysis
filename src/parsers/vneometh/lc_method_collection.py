import pandas as pd
import pickle
import h5py
import json
from pathlib import Path
from typing import Dict, List, Optional, Union
from .vneo_method import VNeoMethod
import zipfile
import tempfile
import matplotlib.pyplot as plt



class VNeoMethodCollection:
    """Collection of LC methods with storage and comparison capabilities."""

    def __init__(self):
        """Initialize empty method collection."""
        self.methods: Dict[str, VNeoMethod] = {}

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

    def compare_gradients(self, method_names: Optional[List[str]] = None) -> pd.DataFrame:
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

        all_gradients = []
        for name in method_names:
            if name in self.methods:
                gradient = self.methods[name].gradient.copy()
                gradient['Method'] = name
                all_gradients.append(gradient)

        if all_gradients:
            return pd.concat(all_gradients, ignore_index=True)
        return pd.DataFrame()

    def compare_gradients_wide(self, method_names: Optional[List[str]] = None,
                               columns: Optional[List[str]] = None) -> Dict[str, pd.DataFrame]:
        """
        Compare gradient profiles in wide format (side-by-side).

        For each gradient column (e.g., %B, Flow), creates a separate DataFrame
        with time points as rows and methods as columns.

        Parameters:
        -----------
        method_names : List[str], optional
            Methods to compare. If None, compare all methods.
        columns : List[str], optional
            Specific gradient columns to compare. If None, compares all numeric columns.

        Returns:
        --------
        Dict[str, pd.DataFrame]
            Dictionary mapping column names to comparison DataFrames
            Each DataFrame has time points as rows and methods as columns

        Example:
        --------
        result = collection.compare_gradients_wide(['method1', 'method2'])
        print(result['%B'])  # Compare %B across time
        """
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

    def plot_gradients(self, method_names: Optional[List[str]] = None,
                      x_col: Optional[Union[str, List[str]]] = None,
                      y_cols: Optional[Union[str, List[str]]] = None,
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

        if method_names is None:
            method_names = self.list_methods()

        if not method_names:
            print("Warning: No methods to plot")
            return None

        first_method = self.methods[method_names[0]]

        # Determine x-axis column(s)
        if x_col is None:
            # Find time column (case-insensitive)
            for c in first_method.gradient.columns:
                if 'time' in c.lower():
                    x_col = c
                    break
            if x_col is None:
                print("Warning: Could not find time column. Please specify x_col parameter.")
                return None
        
        # Convert x_col to list if it's a string
        if isinstance(x_col, str):
            x_cols = [x_col]
        else:
            x_cols = x_col

        # Validate x columns
        for col in x_cols:
            if col not in first_method.gradient.columns:
                print(f"Warning: X column '{col}' not found in gradient data.")
                return None

        # Determine y-axis column(s)
        if y_cols is None:
            # Try to find %B column
            b_cols = [col for col in first_method.gradient.columns
                     if '%B' in col or 'Percent B' in col]
            if b_cols:
                y_cols = [b_cols[0]]
            else:
                print("Warning: Could not find %B column. Please specify y_cols parameter.")
                return None
        elif isinstance(y_cols, str):
            y_cols = [y_cols]

        # Validate y columns
        for col in y_cols:
            if col not in first_method.gradient.columns:
                print(f"Warning: Y column '{col}' not found in gradient data.")
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
        colors = plt.cm.tab10(range(len(method_names)))
        for i, name in enumerate(method_names):
            if name in self.methods:
                method = self.methods[name]

                # Handle multiple x and y column combinations
                # If we have multiple x cols and multiple y cols, pair them up
                # Otherwise, use all combinations
                if len(x_cols) > 1 and len(y_cols) > 1 and len(x_cols) == len(y_cols):
                    # Pair x_cols and y_cols: x[0] with y[0], x[1] with y[1], etc.
                    column_pairs = list(zip(x_cols, y_cols))
                else:
                    # Use all combinations of x and y columns
                    column_pairs = [(x_col, y_col) for x_col in x_cols for y_col in y_cols]

                for pair_idx, (x_col, y_col) in enumerate(column_pairs):
                    # Check if columns exist in this method
                    if x_col not in method.gradient.columns:
                        print(f"Warning: x_col '{x_col}' not found in method '{name}', skipping")
                        continue
                    
                    if y_col not in method.gradient.columns:
                        print(f"Warning: y_col '{y_col}' not found in method '{name}', skipping")
                        continue

                    # Select which axis to use for this y column
                    y_idx = y_cols.index(y_col) if y_col in y_cols else 0
                    if twin_axes and len(y_cols) > 1:
                        current_ax = axes[min(y_idx, len(axes) - 1)]
                    else:
                        current_ax = ax

                    # Create label
                    if len(column_pairs) > 1:
                        if len(x_cols) > 1 and len(y_cols) > 1:
                            # Multiple x and y: include both in label
                            x_label = x_col.split('.')[-1] if '.' in x_col else x_col
                            y_label = y_col.split('.')[-1] if '.' in y_col else y_col
                            label = f"{name} ({x_label} vs {y_label})"
                        elif len(y_cols) > 1:
                            # Multiple y columns: include y column in label
                            y_label = y_col.split('.')[-1] if '.' in y_col else y_col
                            label = f"{name} ({y_label})"
                        elif len(x_cols) > 1:
                            # Multiple x columns: include x column in label
                            x_label = x_col.split('.')[-1] if '.' in x_col else x_col
                            label = f"{name} ({x_label})"
                        else:
                            label = name
                    else:
                        label = name

                    # Plot line
                    plot_kwargs = {
                        'label': label,
                        'color': colors[i],
                        'linewidth': 2,
                        'alpha': 0.8
                    }

                    # Adjust line style if multiple pairs per method
                    if len(column_pairs) > 1:
                        linestyles = ['-', '--', '-.', ':']
                        plot_kwargs['linestyle'] = linestyles[pair_idx % len(linestyles)]

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
            xlabel = x_cols[0].split('.')[-1] if '.' in x_cols[0] else x_cols[0]
        else:
            xlabel = "X Value"
        ax.set_xlabel(xlabel)

        # Set y-axis labels
        if twin_axes and len(y_cols) > 1:
            # Set labels for each axis
            for y_idx, y_col in enumerate(y_cols):
                if y_idx < len(axes):
                    ylabel = y_col.split('.')[-1] if '.' in y_col else y_col
                    axes[y_idx].set_ylabel(ylabel)
                    axes[y_idx].legend(loc=f'upper {"left" if y_idx == 0 else "right"}')
        else:
            if len(y_cols) == 1:
                ylabel = y_cols[0].split('.')[-1] if '.' in y_cols[0] else y_cols[0]
                ax.set_ylabel(ylabel)
            else:
                ax.set_ylabel('Value')
            ax.legend(loc='best')

        # Create informative title
        if len(x_cols) == 1 and len(y_cols) == 1:
            title = f'Gradient Comparison: {", ".join(method_names)}'
        else:
            x_desc = f"{len(x_cols)} X-columns" if len(x_cols) > 1 else x_cols[0].split('.')[-1]
            y_desc = f"{len(y_cols)} Y-columns" if len(y_cols) > 1 else y_cols[0].split('.')[-1] 
            title = f'Gradient Comparison ({x_desc} vs {y_desc}): {", ".join(method_names)}'
        ax.set_title(title)
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
        return f"VNeoMethodCollection(n_methods={len(self.methods)})"

    def __getitem__(self, name: str) -> VNeoMethod:
        """Allow dictionary-style access to methods."""
        return self.methods[name]


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
