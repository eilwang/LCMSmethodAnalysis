# DIA-NN data handling
from .bps_loader import BPSLoader
# DiannCollection imports DiannLoader, so import DiannLoader first
try:
    from .bps_collection import BPSCollection
except ImportError:
    # If diann_collection has import issues, create a placeholder
    BPSCollection = None

__all__ = ['BPSLoader', 'BPSCollection']
