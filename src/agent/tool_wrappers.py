"""
Wrappers for existing LC, MS, pressure, and DIA-NN result parsers.
"""

from typing import Any, Dict, Optional, List, Union
from pathlib import Path

# Import method path resolver for LC/MS method files
from src.parsers.method_path_resolver import MethodPathResolver

# Import DIA-NN collection loader
from archive.diann_collection_loader import DiannCollectionLoader

# --- LC Method Wrapper ---
def parse_lc_method(method_path: str) -> Dict[str, Any]:
    """
    Parses an LC method directory or zip file and returns resolved path info.
    """
    with MethodPathResolver(method_path) as resolver:
        resolved = resolver.resolve()
        return {
            "resolved_path": str(resolved),
            "is_zip": resolver.is_zip
        }

# --- MS Method Wrapper (stub, to be implemented with actual parser) ---
def parse_ms_method(method_path: str) -> Dict[str, Any]:
    """
    Parses an MS method directory or zip file and returns resolved path info.
    """
    with MethodPathResolver(method_path) as resolver:
        resolved = resolver.resolve()
        return {
            "resolved_path": str(resolved),
            "is_zip": resolver.is_zip
        }

# --- Pressure Trace Wrapper (stub, to be implemented with actual parser) ---
def parse_pressure_trace(file_path: str) -> Dict[str, Any]:
    """
    Placeholder for pressure trace file parsing.
    """
    # Implement actual parsing logic as needed
    return {"status": "not implemented", "file": file_path}

# --- DIA-NN Results Wrapper ---
def load_diann_results(zip_path: str, level: Optional[str] = None, merge_method: str = 'outer') -> Any:
    """
    Loads and merges DIA-NN results from a zip archive using DiannCollectionLoader.
    """
    with DiannCollectionLoader() as loader:
        return loader.load_from_zip(zip_path, level=level, merge_method=merge_method)
