# DIA-NN data handling
from .anndiannloader import DiannLoader
# DiannCollection imports DiannLoader, so import DiannLoader first
try:
    from .diann_collection import DiannCollection
except ImportError:
    # If diann_collection has import issues, create a placeholder
    DiannCollection = None

__all__ = ['DiannLoader', 'DiannCollection']
