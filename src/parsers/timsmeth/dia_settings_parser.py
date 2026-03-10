"""
DIA Settings Parser for Bruker diaSettings.diasqlite files

This module provides structured access to DIA/diaPASEF acquisition windows
from Bruker TimsTOF diaSettings.diasqlite database files.
"""

import sqlite3
import pandas as pd
from pathlib import Path
from typing import Dict, Optional, Any

from ..method_path_resolver import MethodPathResolver


class DIASettings:
    """Parse and provide structured access to DIA acquisition settings."""

    def __init__(self, method_path: str):
        """
        Initialize with method directory path.

        Parameters:
        -----------
        method_path : str
            Path to the .m method directory, diaSettings.diasqlite file,
            or path to a .zip file containing the method directory
        """
        self.original_path = Path(method_path)

        # Create path resolver to handle both zipped and unzipped methods
        self.resolver = MethodPathResolver(method_path)

        # Resolve the method directory
        method_dir = self.resolver.resolve()

        # If original path was to the database file itself, use it directly
        if self.original_path.suffix == '.diasqlite':
            self.db_path = method_dir.parent / self.original_path.name
        else:
            # Path is to the .m directory
            self.db_path = method_dir / 'diaSettings.diasqlite'

        if not self.db_path.exists():
            raise FileNotFoundError(f"Database file not found: {self.db_path}")

        # Parse database
        self.global_info = self._parse_global_info()
        self.windows = self._parse_windows()
        self.polygon_points = self._parse_polygon()

    def _parse_global_info(self) -> Dict[str, Any]:
        """
        Parse global method information.

        Returns:
        --------
        Dict[str, Any]
            Dictionary of global parameters (1/K0 limits, schema version, etc.)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT Key, Value FROM DiaGlobalMethodInfo")

        global_info = {}
        for key, value in cursor.fetchall():
            # Try to convert to numeric if possible
            try:
                global_info[key] = float(value)
            except (ValueError, TypeError):
                global_info[key] = value

        conn.close()
        return global_info

    def _parse_windows(self) -> pd.DataFrame:
        """
        Parse DIA window specifications.

        Returns:
        --------
        pd.DataFrame
            DataFrame with window specifications including:
            - Id: Window identifier
            - Type: 0=MS1, 1=MS2/DIA
            - CycleId: Acquisition cycle number
            - OneOverK0Start/End: Ion mobility range (1/K0)
            - IsolationMz: Center m/z
            - IsolationWidth: Width in m/z
            - CollisionEnergy: Collision energy in eV
            - WindowType: MS1 or MS2/DIA (derived)
            - MzStart/MzEnd: m/z range (derived)
        """
        conn = sqlite3.connect(self.db_path)

        windows_df = pd.read_sql_query("""
            SELECT
                Id,
                Type,
                CycleId,
                OneOverK0Start,
                OneOverK0End,
                IsolationMz,
                IsolationWidth,
                CollisionEnergy
            FROM DiaWindowsSpecification
            ORDER BY Id
        """, conn)

        conn.close()

        # Add window type labels
        windows_df['WindowType'] = windows_df['Type'].map({0: 'MS1', 1: 'MS2/DIA'})

        # Calculate m/z ranges
        windows_df['MzStart'] = windows_df['IsolationMz'] - windows_df['IsolationWidth'] / 2
        windows_df['MzEnd'] = windows_df['IsolationMz'] + windows_df['IsolationWidth'] / 2

        return windows_df

    def _parse_polygon(self) -> Optional[pd.DataFrame]:
        """
        Parse polygon specification points (if any).

        Returns:
        --------
        Optional[pd.DataFrame]
            DataFrame with polygon points (Mass, Mobility) or None if not defined
        """
        conn = sqlite3.connect(self.db_path)

        polygon_df = pd.read_sql_query("""
            SELECT Id, Mass, Mobility
            FROM DiaParametersPolyonSpecification
            ORDER BY Id
        """, conn)

        conn.close()

        return polygon_df if len(polygon_df) > 0 else None

    def get_ms1_windows(self) -> pd.DataFrame:
        """
        Get MS1 windows only.

        Returns:
        --------
        pd.DataFrame
            DataFrame of MS1 windows
        """
        return self.windows[self.windows['Type'] == 0].copy()

    def get_dia_windows(self) -> pd.DataFrame:
        """
        Get DIA/MS2 windows only.

        Returns:
        --------
        pd.DataFrame
            DataFrame of DIA windows
        """
        return self.windows[self.windows['Type'] == 1].copy()

    def get_windows_by_cycle(self, cycle_id: int) -> pd.DataFrame:
        """
        Get windows for a specific cycle.

        Parameters:
        -----------
        cycle_id : int
            Cycle identifier

        Returns:
        --------
        pd.DataFrame
            Windows in the specified cycle
        """
        return self.windows[self.windows['CycleId'] == cycle_id].copy()

    def get_cycle_ids(self) -> list:
        """
        Get list of unique cycle IDs (includes both MS1 and MS2/DIA windows).

        Returns:
        --------
        list
            Sorted list of cycle IDs
        """
        return sorted(self.windows['CycleId'].dropna().unique().tolist())

    def get_dia_cycle_ids(self) -> list:
        """
        Get list of unique cycle IDs for DIA/MS2 windows only (excludes MS1).

        Returns:
        --------
        list
            Sorted list of cycle IDs from DIA/MS2 windows only
        """
        dia_windows = self.get_dia_windows()
        if len(dia_windows) > 0:
            return sorted(dia_windows['CycleId'].dropna().unique().tolist())
        return []

    def to_dict(self) -> Dict[str, Any]:
        """
        Export all data as a dictionary.

        Returns:
        --------
        Dict[str, Any]
            Complete DIA settings data structure
        """
        return {
            'global_info': self.global_info,
            'windows': self.windows.to_dict('records'),
            'polygon_points': self.polygon_points.to_dict('records') if self.polygon_points is not None else None
        }

    def summary(self) -> str:
        """Return summary of DIA settings."""
        summary_lines = []
        summary_lines.append("DIA Settings Summary")
        summary_lines.append("=" * 70)

        # Global info
        summary_lines.append("\nGlobal Parameters:")
        summary_lines.append(f"  Schema: {self.global_info.get('SchemaType', 'N/A')}")
        summary_lines.append(f"  Version: {self.global_info.get('SchemaVersionMajor', '?')}.{self.global_info.get('SchemaVersionMinor', '?')}")
        summary_lines.append(f"  1/K0 Range: {self.global_info.get('OneOverK0LowerLimit', 'N/A'):.2f} - {self.global_info.get('OneOverK0UpperLimit', 'N/A'):.2f}")

        # Window counts
        ms1_count = len(self.get_ms1_windows())
        dia_count = len(self.get_dia_windows())
        summary_lines.append(f"\nWindows:")
        summary_lines.append(f"  Total: {len(self.windows)}")
        summary_lines.append(f"  MS1: {ms1_count}")
        summary_lines.append(f"  DIA/MS2: {dia_count}")

        # Cycle info
        cycle_ids = self.get_cycle_ids()
        if cycle_ids:
            summary_lines.append(f"  Unique cycles: {len(cycle_ids)} ({min(cycle_ids)} - {max(cycle_ids)})")

        # DIA window ranges
        if dia_count > 0:
            dia_windows = self.get_dia_windows()
            summary_lines.append("\nDIA Window Ranges:")
            summary_lines.append(f"  m/z: {dia_windows['MzStart'].min():.1f} - {dia_windows['MzEnd'].max():.1f}")
            summary_lines.append(f"  1/K0: {dia_windows['OneOverK0Start'].min():.2f} - {dia_windows['OneOverK0End'].max():.2f}")
            summary_lines.append(f"  Collision Energy: {dia_windows['CollisionEnergy'].min():.1f} - {dia_windows['CollisionEnergy'].max():.1f} eV")

        # Polygon info
        if self.polygon_points is not None:
            summary_lines.append(f"\nPolygon Definition: {len(self.polygon_points)} points")

        return '\n'.join(summary_lines)

    def plot_windows(self, ax=None, show_labels: bool = False,
                     color_by_cycle: bool = True, uniform_color: str = 'steelblue',
                     alpha: float = 0.6, edge_color: str = 'white',
                     linewidth: float = 0.5,
                     method_name: Optional[str] = None,
                     figsize=(12, 8)):
        """
        Plot DIA windows in m/z vs ion mobility (1/K0) space.

        Parameters:
        -----------
        ax : matplotlib.axes.Axes, optional
            External axis to plot on. If None, creates new figure.
        show_labels : bool
            Whether to show cycle ID labels on windows (default: False)
        color_by_cycle : bool
            If True, color windows by cycle ID. If False, use uniform_color (default: True)
        uniform_color : str
            Color to use when color_by_cycle=False (default: 'steelblue')
        alpha : float
            Transparency of window fills, 0-1 (default: 0.6)
        edge_color : str
            Color of window outlines (default: 'white')
        linewidth : float
            Width of window outline lines (default: 0.5)
        method_name : str, optional
            Method name to include in legend. Useful when plotting multiple methods
            on same axis for comparison.
        figsize : tuple
            Figure size if creating new figure (default: (12, 8))

        Returns:
        --------
        matplotlib.axes.Axes
            The axis object with the plot
        """
        import matplotlib.pyplot as plt
        import matplotlib.cm as cm
        import numpy as np

        # Create figure if no axis provided
        if ax is None:
            fig, ax = plt.subplots(figsize=figsize)

        # Get DIA windows only
        dia_windows = self.get_dia_windows()

        if len(dia_windows) == 0:
            ax.text(0.5, 0.5, 'No DIA windows available',
                   ha='center', va='center', transform=ax.transAxes)
            return ax

        # Get unique cycle IDs and create color map
        cycle_ids = sorted(dia_windows['CycleId'].dropna().unique())

        if color_by_cycle:
            n_cycles = len(cycle_ids)

            # Use a colormap with good color separation
            if n_cycles <= 10:
                cmap = cm.tab10
            elif n_cycles <= 20:
                cmap = cm.tab20
            else:
                cmap = cm.viridis

            # Create color mapping for cycles
            cycle_colors = {cycle_id: cmap(i / max(n_cycles - 1, 1))
                           for i, cycle_id in enumerate(cycle_ids)}
        else:
            # Use uniform color for all windows
            cycle_colors = {cycle_id: uniform_color for cycle_id in cycle_ids}

        # Plot each window as a rectangle
        for idx, row in dia_windows.iterrows():
            mz_start = row['MzStart']
            mz_end = row['MzEnd']
            k0_start = row['OneOverK0Start']
            k0_end = row['OneOverK0End']
            cycle_id = row['CycleId']

            # Skip if any values are NaN
            if pd.isna([mz_start, mz_end, k0_start, k0_end]).any():
                continue

            # Get color for this cycle
            color = cycle_colors.get(cycle_id, 'gray')

            # Create rectangle
            rect = plt.Rectangle((mz_start, k0_start),
                                mz_end - mz_start,
                                k0_end - k0_start,
                                facecolor=color,
                                edgecolor=edge_color,
                                alpha=alpha,
                                linewidth=linewidth)
            ax.add_patch(rect)

            # Add cycle ID label
            if show_labels:
                # Determine text color based on background brightness
                # Convert color to RGB if it's a string
                import matplotlib.colors as mcolors
                if isinstance(color, str):
                    rgb = mcolors.to_rgb(color)
                else:
                    rgb = color[:3]
                text_color = 'white' if np.mean(rgb) < 0.5 else 'black'

                ax.text((mz_start + mz_end) / 2, (k0_start + k0_end) / 2,
                       f'C{int(cycle_id)}',
                       ha='center', va='center',
                       fontsize=8, fontweight='bold',
                       color=text_color)

        # Set labels and title
        ax.set_xlabel('m/z', fontsize=12, fontweight='bold')
        ax.set_ylabel('1/K0 (Ion Mobility)', fontsize=12, fontweight='bold')
        ax.set_title('DIA Windows in m/z × Ion Mobility Space',
                    fontsize=14, fontweight='bold')
        ax.grid(alpha=0.3)

        # Set axis limits with padding
        ax.set_xlim(dia_windows['MzStart'].min() - 50,
                   dia_windows['MzEnd'].max() + 50)
        ax.set_ylim(self.global_info['OneOverK0LowerLimit'] - 0.05,
                   self.global_info['OneOverK0UpperLimit'] + 0.05)

        # Add legend
        from matplotlib.patches import Patch

        if color_by_cycle:
            # Legend with cycle colors
            if method_name:
                # Include method name in labels
                legend_elements = [Patch(facecolor=cycle_colors[cycle_id],
                                        edgecolor=edge_color,
                                        alpha=alpha,
                                        label=f'{method_name} - Cycle {int(cycle_id)}')
                                  for cycle_id in cycle_ids]
            else:
                # Just cycle IDs
                legend_elements = [Patch(facecolor=cycle_colors[cycle_id],
                                        edgecolor=edge_color,
                                        alpha=alpha,
                                        label=f'Cycle {int(cycle_id)}')
                                  for cycle_id in cycle_ids]
            ax.legend(handles=legend_elements, loc='best', fontsize=9)
        elif method_name:
            # Uniform color with method name - create legend entry
            legend_element = Patch(facecolor=uniform_color,
                                  edgecolor=edge_color,
                                  alpha=alpha,
                                  label=method_name)
            ax.legend(handles=[legend_element], loc='best', fontsize=9)

        return ax

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
        ms1_count = len(self.get_ms1_windows())
        dia_count = len(self.get_dia_windows())
        return f"DIASettings(windows={len(self.windows)}, MS1={ms1_count}, DIA={dia_count})"


# Convenience function for backward compatibility
def parse_dia_settings(method_dir: str) -> Dict[str, Any]:
    """
    Parse diaSettings.diasqlite database (functional interface).

    Parameters:
    -----------
    method_dir : str
        Path to the .m method directory

    Returns:
    --------
    dict
        Dictionary containing:
        - global_info: Dictionary of global method parameters
        - windows: DataFrame of DIA window specifications
        - polygon_points: DataFrame of polygon specification points (if any)
    """
    settings = DIASettings(method_dir)
    return {
        'global_info': settings.global_info,
        'windows': settings.windows,
        'polygon_points': settings.polygon_points
    }


# Usage example
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        method_path = sys.argv[1]
    else:
        # Default path for testing
        method_path = "/Users/eileen.wang/Desktop/diann/SampleData/methods/MS/DIA003.proteoscape.m"

    # Parse DIA settings
    settings = DIASettings(method_path)

    # Print summary
    print(settings.summary())

    # Show DIA windows
    print("\n" + "=" * 70)
    print("\nDIA Windows (first 10):")
    dia_windows = settings.get_dia_windows()
    print(dia_windows.head(10))

    # Example: Get windows for a specific cycle
    print("\n" + "=" * 70)
    cycle_ids = settings.get_cycle_ids()
    if cycle_ids:
        first_cycle = cycle_ids[0]
        print(f"\nWindows in Cycle {first_cycle}:")
        cycle_windows = settings.get_windows_by_cycle(first_cycle)
        print(cycle_windows)
