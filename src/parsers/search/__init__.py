# Search data handling (DIA-NN, Spectronaut, etc.)
from .search_loader import SearchLoader
# Import SearchCollection with fallback for missing dependencies
try:
    from .search_collection import SearchCollection
except ImportError:
    # If search_collection has import issues, create a placeholder
    SearchCollection = None

__all__ = ['SearchLoader', 'SearchCollection']
