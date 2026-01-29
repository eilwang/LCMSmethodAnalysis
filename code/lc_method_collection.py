import pandas as pd
import pickle
import h5py
import json
from pathlib import Path
from typing import Dict, List, Optional, Union
from vneo_method_parser import LCMethod


class LCMethodCollection:
    """Collection of LC methods with storage and comparison capabilities."""

    def __init__(self):
        """Initialize empty method collection."""
        self.methods: Dict[str, LCMethod] = {}

    @classmethod
    def from_file(cls, filepath: str) -> 'LCMethodCollection':
        """
        Create a new collection from a saved file.

        Parameters:
        -----------
        filepath : str
            Path to saved collection file (.pkl, .h5, .json)

        Returns:
        --------
        LCMethodCollection
            New collection loaded from file

        Example:
        --------
        collection = LCMethodCollection.from_file('methods.pkl')
        """
        collection = cls()
        collection.load(filepath)
        return collection

    def add_method(self, name: str, method: Union[str, LCMethod], overwrite: bool = False):
        """
        Add a method to the collection.

        Parameters:
        -----------
        name : str
            Identifier for the method
        method : str or LCMethod
            Path to .meth file or LCMethod object
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
            method = LCMethod(method)
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
        Add multiple methods from a folder containing .meth files.

        Parameters:
        -----------
        folder_path : str
            Path to folder containing .meth files
        overwrite : bool
            If True, overwrite existing methods with same names.
            If False, raise error if any method already exists.
        """
        folder = Path(folder_path)
        meth_files = {f.stem: str(f) for f in folder.glob("*.meth")}
        self.add_methods_from_paths(meth_files, overwrite=overwrite)
        
    def get_method(self, name: str) -> Optional[LCMethod]:
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

    def compare_gradients(self, method_names: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Compare gradient profiles across methods.

        Parameters:
        -----------
        method_names : List[str], optional
            Methods to compare. If None, compare all methods.

        Returns:
        --------
        pd.DataFrame
            Combined gradient table with method names
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

        Note: This loads method data as dictionaries, not LCMethod objects.
        To reconstruct LCMethod objects, use load_hdf5_as_objects().

        Parameters:
        -----------
        filepath : str
            Input HDF5 file path
        """
        self.methods = {}

        with h5py.File(filepath, 'r') as f:
            for name in f.keys():
                grp = f[name]

                # Create a pseudo-LCMethod object with the data
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

        Note: This loads method data as dictionaries, not LCMethod objects.

        Parameters:
        -----------
        filepath : str
            Input JSON file path
        """
        with open(filepath, 'r') as f:
            data = json.load(f)

        self.methods = {}
        for name, method_data in data.items():
            # Create a pseudo-LCMethod object with the data
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
        return f"LCMethodCollection(n_methods={len(self.methods)})"

    def __getitem__(self, name: str) -> LCMethod:
        """Allow dictionary-style access to methods."""
        return self.methods[name]


# Usage example
if __name__ == "__main__":
    # Create collection
    collection = LCMethodCollection()

    # Add methods from paths
    collection.add_methods_from_paths({
        'method1': 'path/to/method1.meth',
        'method2': 'path/to/method2.meth'
    })

    # Or add individual methods
    collection.add_method('method3', LCMethod('path/to/method3.meth'))

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
    new_collection = LCMethodCollection()
    new_collection.load('methods.pkl')  # Auto-detects pickle format

    # Or create collection directly from file
    loaded_collection = LCMethodCollection.from_file('methods.h5')

    # Or use specific loader if preferred
    another_collection = LCMethodCollection()
    another_collection.load_json('methods.json')

    # Access methods
    method = new_collection['method1']
    print(f"Runtime: {method.runtime}")
    print(f"Gradient:\n{method.gradient}")
