"""
Method Path Resolver - Unified zip/directory handling for method parsers

This module provides transparent access to method files whether they are:
- Uncompressed directories (.m folders)
- Compressed zip archives (.zip files)
- Individual method files within either format

All method parsers (LC, MS, DIA, Synchro) can use this to seamlessly
handle both zipped and unzipped method files.
"""

from pathlib import Path
from typing import Union, Optional, BinaryIO
import zipfile
import tempfile
import shutil
from contextlib import contextmanager


class MethodPathResolver:
    """
    Resolves paths to method files, handling both zipped and unzipped formats.

    This class provides transparent access to method files whether they exist
    in a directory or within a zip archive.
    """

    def __init__(self, path: Union[str, Path]):
        """
        Initialize with a path to a method directory or zip file.

        Parameters:
        -----------
        path : str or Path
            Path to:
            - A .m method directory
            - A .zip file containing a .m directory
            - A specific method file (e.g., .method, .diasqlite, .meth)
        """
        self.original_path = Path(path)
        self.is_zip = False
        self.zip_file = None
        self.temp_dir = None
        self.resolved_path = None

        # Determine if we're dealing with a zip file
        if self.original_path.suffix == '.zip':
            self.is_zip = True
            self.zip_file = zipfile.ZipFile(self.original_path, 'r')
        elif not self.original_path.exists():
            # Check if there's a zip file with the same base name
            potential_zip = self.original_path.with_suffix('.zip')
            if potential_zip.exists():
                self.is_zip = True
                self.zip_file = zipfile.ZipFile(potential_zip, 'r')

    def resolve(self, relative_path: Optional[str] = None) -> Path:
        """
        Resolve a path to a method file.

        If the method is zipped, extracts to a temporary directory.

        Parameters:
        -----------
        relative_path : str, optional
            Relative path within the method directory (e.g., 'diaSettings.diasqlite')
            If None, returns the method directory itself.

        Returns:
        --------
        Path
            Absolute path to the requested file/directory
        """
        if not self.is_zip:
            # Direct file access
            if relative_path:
                return self.original_path / relative_path
            return self.original_path

        # Extract from zip if needed
        if self.temp_dir is None:
            self.temp_dir = tempfile.mkdtemp(prefix='bruker_method_')
            self.zip_file.extractall(self.temp_dir)

            # Find the .m directory within the extracted content
            temp_path = Path(self.temp_dir)
            m_dirs = list(temp_path.glob('*.m'))

            if m_dirs:
                self.resolved_path = m_dirs[0]
            else:
                # Maybe the zip contains files directly
                self.resolved_path = temp_path

        if relative_path:
            return self.resolved_path / relative_path
        return self.resolved_path

    def exists(self, relative_path: str) -> bool:
        """
        Check if a file exists within the method directory.

        Parameters:
        -----------
        relative_path : str
            Relative path to check (e.g., 'diaSettings.diasqlite')

        Returns:
        --------
        bool
            True if file exists
        """
        if not self.is_zip:
            return (self.original_path / relative_path).exists()

        # Check in zip file
        # Get the base .m directory name in zip
        m_dirs = [name for name in self.zip_file.namelist() if '.m/' in name]
        if m_dirs:
            base_dir = m_dirs[0].split('.m/')[0] + '.m/'
            full_path = base_dir + relative_path
            return full_path in self.zip_file.namelist()

        return relative_path in self.zip_file.namelist()

    def read_bytes(self, relative_path: str) -> bytes:
        """
        Read a file as bytes.

        Parameters:
        -----------
        relative_path : str
            Relative path to file

        Returns:
        --------
        bytes
            File contents
        """
        if not self.is_zip:
            return (self.original_path / relative_path).read_bytes()

        # Read from zip
        m_dirs = [name for name in self.zip_file.namelist() if '.m/' in name]
        if m_dirs:
            base_dir = m_dirs[0].split('.m/')[0] + '.m/'
            full_path = base_dir + relative_path
        else:
            full_path = relative_path

        return self.zip_file.read(full_path)

    def cleanup(self):
        """Clean up temporary files if they were created."""
        if self.temp_dir and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
        if self.zip_file:
            self.zip_file.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup temp files."""
        self.cleanup()

    def __del__(self):
        """Destructor - cleanup temp files."""
        self.cleanup()


@contextmanager
def method_path_context(path: Union[str, Path]):
    """
    Context manager for method path resolution.

    Automatically handles cleanup of temporary files.

    Usage:
    ------
    with method_path_context('/path/to/method.zip') as resolver:
        method_dir = resolver.resolve()
        # Use method_dir...
    # Temporary files automatically cleaned up

    Parameters:
    -----------
    path : str or Path
        Path to method directory or zip file

    Yields:
    -------
    MethodPathResolver
        Resolver instance
    """
    resolver = MethodPathResolver(path)
    try:
        yield resolver
    finally:
        resolver.cleanup()


# Convenience function for simple use cases
def resolve_method_path(path: Union[str, Path],
                       auto_extract: bool = True) -> Path:
    """
    Resolve a method path, handling zipped archives.

    Parameters:
    -----------
    path : str or Path
        Path to method directory or zip file
    auto_extract : bool
        If True, extracts zip to temp directory (default: True)
        Note: Caller is responsible for cleanup if not using context manager

    Returns:
    --------
    Path
        Resolved path to method directory

    Warning:
    --------
    If auto_extract=True and path is zipped, temporary files are created.
    Use method_path_context() context manager for automatic cleanup.
    """
    resolver = MethodPathResolver(path)
    return resolver.resolve()


# Usage example
if __name__ == "__main__":
    import sys

    # Test with either directory or zip
    if len(sys.argv) > 1:
        test_path = sys.argv[1]
    else:
        print("Usage: python method_path_resolver.py <path_to_method_dir_or_zip>")
        sys.exit(1)

    print(f"Testing with: {test_path}")
    print("=" * 70)

    # Using context manager (recommended)
    with method_path_context(test_path) as resolver:
        method_dir = resolver.resolve()
        print(f"Resolved path: {method_dir}")
        print(f"Is from zip: {resolver.is_zip}")

        # Check for common files
        common_files = [
            'microTOFQImpacTemAcquisition.method',
            'diaSettings.diasqlite',
            'synchroSettings.syncsqlite'
        ]

        print("\nFile existence check:")
        for filename in common_files:
            exists = resolver.exists(filename)
            print(f"  {filename}: {'✓' if exists else '✗'}")

    print("\n✓ Temporary files cleaned up automatically")
