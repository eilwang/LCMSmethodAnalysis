# DIA-NN data handling
from .search_loader import BPSLoader
# DiannCollection imports DiannLoader, so import DiannLoader first
try:
    from .search_collection import BPSCollection
except ImportError:
    # If diann_collection has import issues, create a placeholder
    BPSCollection = None

__all__ = ['BPSLoader', 'BPSCollection']
