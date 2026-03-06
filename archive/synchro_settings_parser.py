"""
Synchro Settings Parser for Bruker synchroSettings.syncsqlite files

This module provides structured access to synchronization settings
from Bruker TimsTOF synchroSettings.syncsqlite database files.

Note: In many cases, this database may be empty (initialized but unused),
particularly when no instrument synchronization is configured.
"""

import sqlite3
import pandas as pd
from pathlib import Path
from typing import Dict, Optional, Any, List

from LCMSmethodAnalysis.code.archive.method_path_resolver import MethodPathResolver


class SynchroSettings:
    """Parse and provide structured access to synchronization settings."""

    def __init__(self, method_path: str):
        """
        Initialize with method directory path.

        Parameters:
        -----------
        method_path : str
            Path to the .m method directory, synchroSettings.syncsqlite file,
            or path to a .zip file containing the method directory
        """
        self.original_path = Path(method_path)

        # Create path resolver to handle both zipped and unzipped methods
        self.resolver = MethodPathResolver(method_path)

        # Resolve the method directory
        method_dir = self.resolver.resolve()

        # If original path was to the database file itself, use it directly
        if self.original_path.suffix == '.syncsqlite':
            self.db_path = method_dir.parent / self.original_path.name
        else:
            # Path is to the .m directory
            self.db_path = method_dir / 'synchroSettings.syncsqlite'

        if not self.db_path.exists():
            raise FileNotFoundError(f"Database file not found: {self.db_path}")

        # Discover database structure
        self.tables = self._discover_tables()
        self.is_empty = len(self.tables) == 0

        # Parse available data
        self.data = self._parse_all_tables()

    def _discover_tables(self) -> List[str]:
        """
        Discover all tables in the database.

        Returns:
        --------
        List[str]
            List of table names
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        return tables

    def _parse_all_tables(self) -> Dict[str, pd.DataFrame]:
        """
        Parse all tables in the database.

        Returns:
        --------
        Dict[str, pd.DataFrame]
            Dictionary mapping table names to DataFrames
        """
        if self.is_empty:
            return {}

        conn = sqlite3.connect(self.db_path)
        data = {}

        for table_name in self.tables:
            try:
                df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
                data[table_name] = df
            except Exception as e:
                print(f"Warning: Could not parse table '{table_name}': {e}")

        conn.close()
        return data

    def get_table(self, table_name: str) -> Optional[pd.DataFrame]:
        """
        Get a specific table as a DataFrame.

        Parameters:
        -----------
        table_name : str
            Name of the table to retrieve

        Returns:
        --------
        Optional[pd.DataFrame]
            DataFrame of the table, or None if not found
        """
        return self.data.get(table_name)

    def get_table_names(self) -> List[str]:
        """
        Get list of all table names.

        Returns:
        --------
        List[str]
            List of table names
        """
        return list(self.data.keys())

    def query(self, sql: str) -> pd.DataFrame:
        """
        Execute a custom SQL query on the database.

        Parameters:
        -----------
        sql : str
            SQL query to execute

        Returns:
        --------
        pd.DataFrame
            Query results
        """
        conn = sqlite3.connect(self.db_path)
        result = pd.read_sql_query(sql, conn)
        conn.close()
        return result

    def get_schema(self) -> Dict[str, str]:
        """
        Get schema information for all tables.

        Returns:
        --------
        Dict[str, str]
            Dictionary mapping table names to their CREATE TABLE statements
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        schema = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        return schema

    def to_dict(self) -> Dict[str, Any]:
        """
        Export all data as a dictionary.

        Returns:
        --------
        Dict[str, Any]
            Complete synchronization settings data structure
        """
        return {
            'tables': self.tables,
            'is_empty': self.is_empty,
            'data': {name: df.to_dict('records') for name, df in self.data.items()}
        }

    def summary(self) -> str:
        """Return summary of synchronization settings."""
        summary_lines = []
        summary_lines.append("Synchro Settings Summary")
        summary_lines.append("=" * 70)

        # Database info
        summary_lines.append(f"\nDatabase: {self.db_path.name}")
        summary_lines.append(f"Size: {self.db_path.stat().st_size / 1024:.1f} KB")

        if self.is_empty:
            summary_lines.append("\nStatus: Empty (initialized but no synchronization configured)")
            summary_lines.append("\nNote: This is normal when no instrument synchronization is used.")
        else:
            summary_lines.append(f"\nStatus: Active ({len(self.tables)} table(s))")
            summary_lines.append("\nTables:")
            for table_name in self.tables:
                df = self.data.get(table_name)
                if df is not None:
                    row_count = len(df)
                    col_count = len(df.columns)
                    summary_lines.append(f"  - {table_name}: {row_count} row(s), {col_count} column(s)")

                    # Show first few columns
                    if col_count > 0:
                        cols = ', '.join(df.columns[:5].tolist())
                        if col_count > 5:
                            cols += f', ... ({col_count - 5} more)'
                        summary_lines.append(f"    Columns: {cols}")

        return '\n'.join(summary_lines)

    def cleanup(self):
        """Clean up temporary files if method was loaded from zip."""
        if self.resolver:
            self.resolver.cleanup()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup temp files."""
        self.cleanup()

    def __del__(self):
        """Destructor - cleanup temp files."""
        self.cleanup()

    def __repr__(self):
        if self.is_empty:
            return f"SynchroSettings(empty=True)"
        else:
            return f"SynchroSettings(tables={len(self.tables)}, rows={sum(len(df) for df in self.data.values())})"


# Convenience function for backward compatibility
def parse_synchro_settings(method_dir: str) -> Dict[str, Any]:
    """
    Parse synchroSettings.syncsqlite database (functional interface).

    Parameters:
    -----------
    method_dir : str
        Path to the .m method directory

    Returns:
    --------
    dict
        Dictionary containing:
        - tables: List of table names
        - is_empty: Boolean indicating if database is empty
        - data: Dictionary of table name to DataFrame
    """
    settings = SynchroSettings(method_dir)
    return {
        'tables': settings.tables,
        'is_empty': settings.is_empty,
        'data': settings.data
    }


# Usage example
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        method_path = sys.argv[1]
    else:
        # Default path for testing
        method_path = "/Users/eileen.wang/Desktop/diann/SampleData/methods/MS/DIA003.proteoscape.m"

    # Parse synchro settings
    settings = SynchroSettings(method_path)

    # Print summary
    print(settings.summary())

    # If not empty, show data
    if not settings.is_empty:
        print("\n" + "=" * 70)
        print("\nData:")
        for table_name in settings.get_table_names():
            print(f"\n{table_name}:")
            print(settings.get_table(table_name))

    # Show schema
    print("\n" + "=" * 70)
    print("\nDatabase Schema:")
    schema = settings.get_schema()
    if schema:
        for table_name, create_sql in schema.items():
            print(f"\n{table_name}:")
            print(create_sql)
    else:
        print("No tables defined (empty database)")
