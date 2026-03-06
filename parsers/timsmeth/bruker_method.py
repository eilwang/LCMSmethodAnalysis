"""
Unified Bruker Method Parser

This module provides a unified interface to parse complete Bruker TimsTOF method
files, combining MS instrument parameters and DIA acquisition settings.
"""

from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd

from LCMSmethodAnalysis.parsers.timsmeth.ms_method import MicroTOFMethod
from dia_settings_parser import DIASettings
from archive.synchro_settings_parser import SynchroSettings
from method_path_resolver import MethodPathResolver


class BrukerMethod:
    """
    Unified parser for Bruker TimsTOF method files.

    This class combines MicroTOFMethod (instrument parameters from XML),
    DIASettings (acquisition windows from SQLite), and optionally
    SynchroSettings (synchronization settings from SQLite).

    Attributes:
    -----------
    method_path : Path
        Path to the .m method directory
    ms : MicroTOFMethod
        MS instrument parameters (calibration, collision cell, TOF, polarity configs)
    dia : DIASettings or None
        DIA acquisition settings (windows, cycles, ion mobility)
    synchro : SynchroSettings or None
        Synchronization settings (if configured)
    """

    def __init__(self, method_path: str, parse_synchro: bool = False):
        """
        Initialize with method directory path.

        Parameters:
        -----------
        method_path : str
            Path to the .m method directory or path to a .zip file containing
            the method directory
        parse_synchro : bool
            Whether to parse synchroSettings (default: False)
        """
        self.method_path = Path(method_path)

        # Validate path exists (either as directory or zip file)
        if not self.method_path.exists():
            # Check if there's a zip file with the same base name
            potential_zip = self.method_path.with_suffix('.zip')
            if not potential_zip.exists():
                raise FileNotFoundError(f"Method directory or zip file not found: {self.method_path}")

        # Parse MS instrument parameters (always present)
        # MicroTOFMethod now handles zip files internally
        self.ms = MicroTOFMethod(self.method_path)

        # Parse DIA settings (if present)
        # Create resolver to check if DIA settings exist
        resolver = MethodPathResolver(self.method_path)
        try:
            if resolver.exists('diaSettings.diasqlite'):
                try:
                    self.dia = DIASettings(self.method_path)
                except Exception as e:
                    print(f"Warning: Could not parse DIA settings: {e}")
                    self.dia = None
            else:
                self.dia = None
        finally:
            resolver.cleanup()

        # Parse synchro settings (optional)
        if parse_synchro:
            resolver = MethodPathResolver(self.method_path)
            try:
                if resolver.exists('synchroSettings.syncsqlite'):
                    try:
                        self.synchro = SynchroSettings(self.method_path)
                    except Exception as e:
                        print(f"Warning: Could not parse synchro settings: {e}")
                        self.synchro = None
                else:
                    self.synchro = None
            finally:
                resolver.cleanup()
        else:
            self.synchro = None

    # ========================================================================
    # Convenience methods for MS parameters
    # ========================================================================

    def get_param(self, param_name: str, polarity: Optional[str] = None,
                  source: str = 'default') -> Optional[Any]:
        """
        Get an MS instrument parameter.

        Parameters:
        -----------
        param_name : str
            Parameter name (permname)
        polarity : Optional[str]
            'positive', 'negative', or None for global parameters
        source : str
            Ion source ('esi', 'apci', etc.), default is 'default'

        Returns:
        --------
        Optional[Any]
            Parameter value or None if not found
        """
        return self.ms.get_param(param_name, polarity, source)

    def get_calibration_info(self, polarity: str = 'negative') -> Dict[str, Any]:
        """Get calibration information for a specific polarity."""
        return self.ms.get_calibration_info(polarity)

    def get_collision_cell_params(self, polarity: str = 'negative') -> Dict[str, Any]:
        """Get collision cell parameters."""
        return self.ms.get_collision_cell_params(polarity)

    def get_tof_params(self, polarity: str = 'negative') -> Dict[str, Any]:
        """Get TOF (Time of Flight) parameters."""
        return self.ms.get_tof_params(polarity)

    def get_ramp_time(self, polarity: str = 'positive') -> Optional[Any]:
        """Get IMS_imeX_RampTime parameter."""
        return self.ms.get_ramp_time(polarity)

    # ========================================================================
    # Convenience methods for DIA settings
    # ========================================================================

    def get_dia_windows(self) -> Optional[pd.DataFrame]:
        """
        Get DIA/MS2 windows only.

        Returns:
        --------
        Optional[pd.DataFrame]
            DataFrame of DIA windows, or None if DIA settings not available
        """
        if self.dia is None:
            return None
        return self.dia.get_dia_windows()

    def get_ms1_windows(self) -> Optional[pd.DataFrame]:
        """
        Get MS1 windows only.

        Returns:
        --------
        Optional[pd.DataFrame]
            DataFrame of MS1 windows, or None if DIA settings not available
        """
        if self.dia is None:
            return None
        return self.dia.get_ms1_windows()

    def get_windows_by_cycle(self, cycle_id: int) -> Optional[pd.DataFrame]:
        """
        Get windows for a specific cycle.

        Parameters:
        -----------
        cycle_id : int
            Cycle identifier

        Returns:
        --------
        Optional[pd.DataFrame]
            Windows in the specified cycle, or None if DIA settings not available
        """
        if self.dia is None:
            return None
        return self.dia.get_windows_by_cycle(cycle_id)

    def get_cycle_ids(self) -> Optional[list]:
        """
        Get list of unique cycle IDs (includes both MS1 and MS2/DIA windows).

        Returns:
        --------
        Optional[list]
            Sorted list of cycle IDs, or None if DIA settings not available
        """
        if self.dia is None:
            return None
        return self.dia.get_cycle_ids()

    def get_dia_cycle_ids(self) -> Optional[list]:
        """
        Get list of unique cycle IDs for DIA/MS2 windows only (excludes MS1).

        Returns:
        --------
        Optional[list]
            Sorted list of cycle IDs from DIA windows only, or None if DIA settings not available
        """
        if self.dia is None:
            return None
        return self.dia.get_dia_cycle_ids()

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
        matplotlib.axes.Axes or None
            The axis object with the plot, or None if DIA settings not available
        """
        if self.dia is None:
            print("Warning: No DIA settings available to plot")
            return None
        return self.dia.plot_windows(ax=ax, show_labels=show_labels,
                                     color_by_cycle=color_by_cycle,
                                     uniform_color=uniform_color,
                                     alpha=alpha, edge_color=edge_color,
                                     linewidth=linewidth,
                                     method_name=method_name,
                                     figsize=figsize)

    # ========================================================================
    # Export methods
    # ========================================================================

    def to_dict(self) -> Dict[str, Any]:
        """
        Export all method data as a dictionary.

        Returns:
        --------
        Dict[str, Any]
            Complete method data structure
        """
        result = {
            'ms_method': self.ms.to_dict(),
            'has_dia': self.dia is not None,
            'has_synchro': self.synchro is not None and not self.synchro.is_empty
        }

        if self.dia is not None:
            result['dia_settings'] = self.dia.to_dict()

        if self.synchro is not None:
            result['synchro_settings'] = self.synchro.to_dict()

        return result

    def to_flat_dict(self, polarity: str = 'positive') -> Dict[str, Any]:
        """
        Export method data as a flat dictionary with only specified polarity.

        All parameters are at the top level. For polarity-specific parameters,
        only the specified polarity values are included.

        Parameters:
        -----------
        polarity : str
            Polarity to extract ('positive' or 'negative'), default: 'positive'

        Returns:
        --------
        Dict[str, Any]
            Flat dictionary with all parameters at top level
        """
        flat = {}

        # Add file info with prefix
        for key, value in self.ms.fileinfo.items():
            flat[f'fileinfo_{key}'] = value

        # Add general info with prefix
        for key, value in self.ms.generalinfo.items():
            flat[f'generalinfo_{key}'] = value

        # Add all MS parameters
        for param_name, value in self.ms.params.items():
            if isinstance(value, dict):
                # Polarity-specific parameter - extract only specified polarity
                if polarity in value:
                    flat[param_name] = value[polarity]
            else:
                # Global parameter
                flat[param_name] = value

        # Add DIA information if available
        if self.dia is not None:
            flat['has_dia'] = True
            flat['dia_windows'] = self.dia.windows
            flat['dia_global_info'] = self.dia.global_info

            # Add DIA summary stats
            dia_windows = self.get_dia_windows()
            if dia_windows is not None and len(dia_windows) > 0:
                flat['dia_window_count'] = len(dia_windows)
                flat['dia_mz_min'] = dia_windows['MzStart'].min()
                flat['dia_mz_max'] = dia_windows['MzEnd'].max()
                flat['dia_im_min'] = dia_windows['OneOverK0Start'].min()
                flat['dia_im_max'] = dia_windows['OneOverK0End'].max()

                # Get cycle info
                dia_cycle_ids = self.get_dia_cycle_ids()
                if dia_cycle_ids:
                    flat['dia_cycle_count'] = len(dia_cycle_ids)
        else:
            flat['has_dia'] = False

        # Add synchro info
        flat['has_synchro'] = self.synchro is not None and not self.synchro.is_empty

        return flat

    def summary(self) -> str:
        """Return comprehensive summary of method."""
        summary_lines = []
        summary_lines.append("=" * 80)
        summary_lines.append("BRUKER TIMSTOF METHOD SUMMARY")
        summary_lines.append("=" * 80)
        summary_lines.append(f"\nMethod Directory: {self.method_path.name}")

        # MS Method section
        summary_lines.append("\n" + "=" * 80)
        summary_lines.append("MS INSTRUMENT PARAMETERS")
        summary_lines.append("=" * 80)
        global_count = sum(1 for v in self.ms.params.values() if not isinstance(v, dict))
        polarity_count = sum(1 for v in self.ms.params.values() if isinstance(v, dict))
        summary_lines.append(f"Total parameters: {len(self.ms.params)} (global={global_count}, polarity_specific={polarity_count})")

        # Show a few key parameters
        summary_lines.append("\nKey Global Parameters:")
        key_params = [
            'Digitizer_SampleIntervall',
            'Collision_GasSupply_Set',
            'TOF_DetectorTofSetValue'
        ]
        for param in key_params:
            value = self.ms.params.get(param)
            if value is not None and not isinstance(value, dict):
                summary_lines.append(f"  {param}: {value}")

        # Capillary voltage by source
        summary_lines.append("\nCapillary Voltages (Negative Mode, ESI):")
        cap_voltage = self.get_param('Source_CapillarySetValue', polarity='negative', source='esi')
        if cap_voltage is not None:
            summary_lines.append(f"  ESI: {cap_voltage} V")

        # DIA Settings section
        if self.dia is not None:
            summary_lines.append("\n" + "=" * 80)
            summary_lines.append("DIA ACQUISITION SETTINGS")
            summary_lines.append("=" * 80)

            summary_lines.append(f"Total windows: {len(self.dia.windows)}")
            summary_lines.append(f"MS1 windows: {len(self.get_ms1_windows())}")
            summary_lines.append(f"DIA windows: {len(self.get_dia_windows())}")

            dia_windows = self.get_dia_windows()
            if len(dia_windows) > 0:
                summary_lines.append(f"\nDIA Window Ranges:")
                summary_lines.append(f"  m/z: {dia_windows['MzStart'].min():.1f} - {dia_windows['MzEnd'].max():.1f}")
                summary_lines.append(f"  1/K0 (Ion Mobility): {dia_windows['OneOverK0Start'].min():.2f} - {dia_windows['OneOverK0End'].max():.2f}")
                if dia_windows['CollisionEnergy'].notna().any():
                    summary_lines.append(f"  Collision Energy: {dia_windows['CollisionEnergy'].min():.1f} - {dia_windows['CollisionEnergy'].max():.1f} eV")

            dia_cycle_ids = self.get_dia_cycle_ids()
            if dia_cycle_ids:
                summary_lines.append(f"  DIA PASEF cycles: {len(dia_cycle_ids)} ({min(dia_cycle_ids)} - {max(dia_cycle_ids)})")
        else:
            summary_lines.append("\n" + "=" * 80)
            summary_lines.append("DIA ACQUISITION SETTINGS: Not Available")
            summary_lines.append("=" * 80)

        # Synchro Settings section
        if self.synchro is not None:
            summary_lines.append("\n" + "=" * 80)
            summary_lines.append("SYNCHRONIZATION SETTINGS")
            summary_lines.append("=" * 80)
            if self.synchro.is_empty:
                summary_lines.append("Status: Empty (no synchronization configured)")
            else:
                summary_lines.append(f"Status: Active ({len(self.synchro.tables)} table(s))")
                for table_name in self.synchro.tables[:3]:  # Show first 3
                    df = self.synchro.data.get(table_name)
                    if df is not None:
                        summary_lines.append(f"  - {table_name}: {len(df)} row(s)")

        summary_lines.append("\n" + "=" * 80)

        return '\n'.join(summary_lines)

    def cleanup(self):
        """Clean up temporary files if method was loaded from zip."""
        if self.ms:
            self.ms.cleanup()
        if self.dia:
            self.dia.cleanup()
        if self.synchro:
            self.synchro.cleanup()

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
        dia_status = f"DIA={len(self.dia.windows)} windows" if self.dia else "DIA=None"
        synchro_status = "Synchro=Active" if (self.synchro and not self.synchro.is_empty) else "Synchro=None"
        return (f"BrukerMethod({self.method_path.name}, "
                f"MS_params={len(self.ms.params)}, "
                f"{dia_status}, {synchro_status})")


# Usage example
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        method_path = sys.argv[1]
    else:
        # Default path for testing
        method_path = "/Users/eileen.wang/Desktop/diann/SampleData/methods/MS/DIA003.proteoscape.m"

    # Parse complete method
    method = BrukerMethod(method_path, parse_synchro=True)

    # Print comprehensive summary
    print(method.summary())

    # Example: Access specific parameters
    print("\n" + "=" * 80)
    print("EXAMPLE PARAMETER ACCESS")
    print("=" * 80)

    print("\n1. Get MS parameter:")
    print(f"   Collision Gas Supply: {method.get_param('Collision_GasSupply_Set')}")
    print(f"   Capillary Voltage (ESI, Negative): {method.get_param('Source_CapillarySetValue', polarity='negative', source='esi')} V")

    if method.dia is not None:
        print("\n2. Get DIA windows:")
        dia_windows = method.get_dia_windows()
        print(f"   DIA windows: {len(dia_windows)}")
        print(f"   First window m/z range: {dia_windows.iloc[0]['MzStart']:.1f} - {dia_windows.iloc[0]['MzEnd']:.1f}")

        print("\n3. Get windows by cycle:")
        cycle_ids = method.get_cycle_ids()
        if cycle_ids:
            first_cycle = cycle_ids[0]
            cycle_windows = method.get_windows_by_cycle(first_cycle)
            print(f"   Cycle {first_cycle} has {len(cycle_windows)} window(s)")

        print("\n4. Plot DIA windows:")
        print("   Creating visualization...")
        ax = method.plot_windows()
        if ax is not None:
            import matplotlib.pyplot as plt
            plt.tight_layout()
            plt.show()
            print("   ✓ Plot created")
