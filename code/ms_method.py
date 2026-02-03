"""
MS Method Parser for Bruker microTOFQImpacTemAcquisition.method files

This module provides structured access to mass spectrometry method parameters
from Bruker TimsTOF instrument method files.
"""

import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any, Union
import pandas as pd
from pathlib import Path

from method_path_resolver import MethodPathResolver


class MicroTOFMethod:
    """Parse and provide structured access to MS method parameters."""

    def __init__(self, method_path: str):
        """
        Initialize with method file path.

        Parameters:
        -----------
        method_path : str
            Path to the .method file (microTOFQImpacTemAcquisition.method),
            path to the parent .m directory, or path to a .zip file containing
            the method directory
        """
        self.original_path = Path(method_path)

        # Create path resolver to handle both zipped and unzipped methods
        self.resolver = MethodPathResolver(method_path)

        # Resolve the method directory
        self.method_dir = self.resolver.resolve()

        # If original path was to the XML file itself, use it directly
        if self.original_path.suffix == '.method':
            xml_path = self.method_dir.parent / self.original_path.name
        else:
            # Path is to the .m directory
            xml_path = self.method_dir / 'microTOFQImpacTemAcquisition.method'

        # Parse XML method
        self.tree = ET.parse(xml_path)
        self.root = self.tree.getroot()

        # Parse sections
        self.fileinfo = self._parse_fileinfo()
        self.generalinfo = self._parse_generalinfo()
        self.instrument_params = self._parse_instrument_params()
        self.polarity_configs = self._parse_polarity_configs()

        # Combine into unified params dictionary
        self.params = self._combine_params()

    def _parse_fileinfo(self) -> Dict[str, str]:
        """Parse fileinfo metadata."""
        fileinfo_elem = self.root.find('fileinfo')
        if fileinfo_elem is None:
            return {}

        return dict(fileinfo_elem.attrib)

    def _parse_generalinfo(self) -> Dict[str, str]:
        """Parse general information section."""
        generalinfo = {}
        generalinfo_elem = self.root.find('generalinfo')

        if generalinfo_elem is not None:
            for child in generalinfo_elem:
                generalinfo[child.tag] = child.text or ""

        return generalinfo

    def _parse_parameter(self, param_elem: ET.Element) -> Union[int, float, str, List]:
        """
        Parse a parameter element based on its type.

        Parameters:
        -----------
        param_elem : ET.Element
            XML element for the parameter

        Returns:
        --------
        Union[int, float, str, List]
            Parsed parameter value
        """
        tag = param_elem.tag
        permname = param_elem.get('permname', '')

        if tag == 'para_int':
            return int(param_elem.get('value', 0))
        elif tag == 'para_double':
            return float(param_elem.get('value', 0.0))
        elif tag == 'para_string':
            return param_elem.get('value', '')
        elif tag == 'para_vec_double':
            return [float(e.get('value', 0.0)) for e in param_elem.findall('entry_double')]
        elif tag == 'para_vec_string':
            return [e.get('value', '') for e in param_elem.findall('entry_string')]
        else:
            return param_elem.get('value', '')

    def _parse_instrument_params(self) -> Dict[str, Any]:
        """
        Parse global instrument parameters (not polarity-specific).

        Returns:
        --------
        Dict[str, Any]
            Dictionary of parameter names to values
        """
        params = {}
        instrument_elem = self.root.find('.//instrument/qtofimpactemacq')

        if instrument_elem is None:
            return params

        # Parse only direct children (not nested in dependent sections)
        for child in instrument_elem:
            if child.tag.startswith('para_') and 'permname' in child.attrib:
                permname = child.attrib['permname']
                params[permname] = self._parse_parameter(child)

        # Also parse timetable segment parameters from method section
        method_elem = self.root.find('.//method/qtofimpactemacq')
        if method_elem is not None:
            timetable_elem = method_elem.find('timetable')
            if timetable_elem is not None:
                for segment in timetable_elem.findall('segment'):
                    for param_elem in segment:
                        if param_elem.tag.startswith('para_') and 'permname' in param_elem.attrib:
                            permname = param_elem.attrib['permname']
                            # Only add if not already present (instrument params take precedence)
                            if permname not in params:
                                params[permname] = self._parse_parameter(param_elem)

        return params

    def _parse_polarity_configs(self) -> Dict[str, Dict[str, Any]]:
        """
        Parse polarity-dependent configurations.

        Returns:
        --------
        Dict[str, Dict[str, Any]]
            Nested dictionary: polarity -> source -> parameters
            Structure: {
                'negative': {'default': {...}, 'esi': {...}, ...},
                'positive': {'default': {...}, 'esi': {...}, ...}
            }
        """
        configs = {}
        instrument_elem = self.root.find('.//instrument/qtofimpactemacq')

        if instrument_elem is None:
            return configs

        # Find all dependent elements recursively
        def parse_dependent_recursive(elem, parent_polarity='', parent_source='default'):
            """Recursively parse dependent elements and their parameters."""
            # Get polarity and source from this element, fallback to parent values
            polarity = elem.get('polarity', parent_polarity)
            source = elem.get('source', parent_source)

            # Initialize config if needed
            if polarity and polarity not in configs:
                configs[polarity] = {}

            # Parse parameters at this level
            params = {}
            for child in elem:
                if child.tag.startswith('para_') and 'permname' in child.attrib:
                    permname = child.attrib['permname']
                    params[permname] = self._parse_parameter(child)
                elif child.tag == 'dependent':
                    # Recursively parse nested dependent element
                    parse_dependent_recursive(child, polarity, source)

            # Store parameters if we have a valid polarity
            if polarity and params:
                if source in configs[polarity]:
                    configs[polarity][source].update(params)
                else:
                    configs[polarity][source] = params

        # Start parsing from all top-level dependent elements
        for dependent_elem in instrument_elem.findall('dependent'):
            parse_dependent_recursive(dependent_elem)

        return configs

    def _combine_params(self) -> Dict[str, Any]:
        """
        Combine instrument_params and polarity_configs into a unified structure.

        Returns a dictionary where:
        - Global parameters are stored as key: value
        - Polarity-specific parameters are stored as {source}_{param}: {'positive': val, 'negative': val}

        Returns:
        --------
        Dict[str, Any]
            Unified parameter dictionary
        """
        combined = {}

        # Add global parameters
        combined.update(self.instrument_params)

        # Organize polarity-specific parameters
        # First, collect all unique (source, param_name) combinations
        param_map = {}  # {source}_{param_name}: {polarity: value}

        for polarity, sources in self.polarity_configs.items():
            for source, params in sources.items():
                for param_name, value in params.items():
                    # Create key as source_paramname
                    key = f"{source}_{param_name}"

                    if key not in param_map:
                        param_map[key] = {}

                    param_map[key][polarity] = value

        # Add polarity-specific parameters to combined dict
        combined.update(param_map)

        return combined

    def get_param(self, param_name: str, polarity: Optional[str] = None,
                  source: str = 'default') -> Optional[Any]:
        """
        Get a parameter value from the unified params dictionary.

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
        # If no polarity specified, look for global parameter first
        if polarity is None:
            # Check if it's a global parameter (not a dict)
            value = self.params.get(param_name)
            if value is not None and not isinstance(value, dict):
                return value
            return None

        # For polarity-specific parameters, construct key as source_paramname
        key = f"{source}_{param_name}"
        value = self.params.get(key)

        # If found and it's a polarity dict, return the specific polarity value
        if isinstance(value, dict) and polarity in value:
            return value[polarity]

        return None

    def get_ramp_time(self, polarity: str = 'positive') -> Optional[float]:
        """
        Get IMS_imeX_RampTime for a specific polarity.

        This parameter is a vector stored in nested dependent elements in the method section.
        Returns the 4th value (index 3) from the vector, which corresponds
        to the ramp time in milliseconds.

        Parameters:
        -----------
        polarity : str
            'positive' or 'negative' (default: 'positive')

        Returns:
        --------
        Optional[float]
            Ramp time in milliseconds, or None if not found
        """
        # Look in method section, not instrument section
        method_elem = self.root.find('.//method/qtofimpactemacq')
        if method_elem is None:
            return None

        # Search for the parameter in dependent elements with matching polarity
        for dependent in method_elem.findall('.//dependent'):
            dep_polarity = dependent.get('polarity', '')
            dep_source = dependent.get('source', 'default')
            if dep_polarity == polarity and dep_source == 'default':
                # Look for IMS_imeX_RampTime vector
                ramp_time_elem = dependent.find('.//para_vec_double[@permname="IMS_imeX_RampTime"]')
                if ramp_time_elem is not None:
                    entries = ramp_time_elem.findall('entry_double')
                    if len(entries) >= 4:
                        try:
                            # Return the 4th value (index 3)
                            return float(entries[3].attrib['value'])
                        except (ValueError, KeyError):
                            pass

        return None

    def get_calibration_info(self, polarity: str = 'negative') -> Dict[str, Any]:
        """
        Extract calibration information for a specific polarity.

        Parameters:
        -----------
        polarity : str
            'positive' or 'negative'

        Returns:
        --------
        Dict[str, Any]
            Dictionary of calibration parameters
        """
        calibration = {}

        if polarity in self.polarity_configs and 'default' in self.polarity_configs[polarity]:
            params = self.polarity_configs[polarity]['default']

            # Extract calibration-related parameters
            for key, value in params.items():
                if key.startswith('Calibration_'):
                    calibration[key] = value

        return calibration

    def get_collision_cell_params(self, polarity: str = 'negative') -> Dict[str, Any]:
        """
        Extract collision cell parameters.

        Parameters:
        -----------
        polarity : str
            'positive' or 'negative'

        Returns:
        --------
        Dict[str, Any]
            Dictionary of collision cell parameters
        """
        collision_params = {}

        # Get global collision parameters
        for key, value in self.instrument_params.items():
            if key.startswith('Collision_'):
                collision_params[key] = value

        # Get polarity-specific collision parameters
        if polarity in self.polarity_configs and 'default' in self.polarity_configs[polarity]:
            params = self.polarity_configs[polarity]['default']
            for key, value in params.items():
                if key.startswith('Collision_'):
                    collision_params[key] = value

        return collision_params

    def get_tof_params(self, polarity: str = 'negative') -> Dict[str, Any]:
        """
        Extract TOF (Time of Flight) parameters.

        Parameters:
        -----------
        polarity : str
            'positive' or 'negative'

        Returns:
        --------
        Dict[str, Any]
            Dictionary of TOF parameters
        """
        tof_params = {}

        # Get global TOF parameters
        for key, value in self.instrument_params.items():
            if key.startswith('TOF_'):
                tof_params[key] = value

        # Get polarity-specific TOF parameters (from calibration)
        if polarity in self.polarity_configs and 'default' in self.polarity_configs[polarity]:
            params = self.polarity_configs[polarity]['default']
            for key, value in params.items():
                if key.startswith('Calibration_TOF_') or key.startswith('TOF_'):
                    tof_params[key] = value

        return tof_params

    def to_dict(self) -> Dict[str, Any]:
        """
        Export all method data as a dictionary.

        Returns:
        --------
        Dict[str, Any]
            Complete method data structure
        """
        return {
            'fileinfo': self.fileinfo,
            'generalinfo': self.generalinfo,
            'params': self.params  # Unified parameter dictionary
        }

    def summary(self) -> str:
        """Return summary of method."""
        summary_lines = []
        summary_lines.append("MS Method Summary")
        summary_lines.append("=" * 70)

        # File info
        summary_lines.append("\nFile Information:")
        summary_lines.append(f"  Type: {self.fileinfo.get('type', 'N/A')}")
        summary_lines.append(f"  Application: {self.fileinfo.get('appname', 'N/A')} v{self.fileinfo.get('appversion', 'N/A')}")
        summary_lines.append(f"  Created: {self.fileinfo.get('createdate', 'N/A')}")

        # General info
        summary_lines.append("\nGeneral Information:")
        summary_lines.append(f"  Organization: {self.generalinfo.get('org', 'N/A')}")
        summary_lines.append(f"  Hostname: {self.generalinfo.get('hostname', 'N/A')}")
        summary_lines.append(f"  Author: {self.generalinfo.get('author', 'N/A')}")
        summary_lines.append(f"  Last Modified: {self.generalinfo.get('modified-by-timstof-on', 'N/A')}")

        # Count parameter types in unified structure
        global_params = sum(1 for v in self.params.values() if not isinstance(v, dict))
        polarity_params = sum(1 for v in self.params.values() if isinstance(v, dict))

        summary_lines.append(f"\nUnified Parameter Structure:")
        summary_lines.append(f"  Global parameters: {global_params}")
        summary_lines.append(f"  Polarity-specific parameters: {polarity_params}")
        summary_lines.append(f"  Total parameters: {len(self.params)}")

        # Key parameters (show both global and polarity-specific examples)
        summary_lines.append("\nKey Parameters:")

        # Global parameters
        global_key_params = [
            'Digitizer_SampleIntervall',
            'Collision_GasSupply_Set',
            'TOF_DetectorTofSetValue'
        ]
        summary_lines.append("  Global:")
        for param in global_key_params:
            value = self.params.get(param)
            if value is not None and not isinstance(value, dict):
                summary_lines.append(f"    {param}: {value}")

        # Example polarity-specific parameters
        summary_lines.append("  Polarity-specific (first 3):")
        count = 0
        for key, value in self.params.items():
            if isinstance(value, dict) and count < 3:
                summary_lines.append(f"    {key}:")
                for pol, val in value.items():
                    val_str = str(val)[:50] + '...' if len(str(val)) > 50 else str(val)
                    summary_lines.append(f"      {pol}: {val_str}")
                count += 1

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
        global_count = sum(1 for v in self.params.values() if not isinstance(v, dict))
        polarity_count = sum(1 for v in self.params.values() if isinstance(v, dict))
        return (f"MicroTOFMethod(params={len(self.params)}, "
                f"global={global_count}, polarity_specific={polarity_count})")


# Usage example
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        method_path = sys.argv[1]
    else:
        # Default path for testing
        method_path = "/Users/eileen.wang/Desktop/diann/SampleData/methods/MS/DIA003.proteoscape.m/microTOFQImpacTemAcquisition.method"

    # Parse method
    method = MicroTOFMethod(method_path)

    # Print summary
    print(method.summary())

    # Example: Get specific parameter
    print("\n" + "=" * 70)
    print("\nExample Parameter Access:")
    print(f"Collision Gas Supply: {method.get_param('Collision_GasSupply_Set')}")
    print(f"Negative Polarity Collision Bias: {method.get_param('Collision_Bias_Set', polarity='negative')}")

    # Get calibration info
    print("\n" + "=" * 70)
    print("\nCalibration Info (Negative):")
    cal_info = method.get_calibration_info('negative')
    for key in list(cal_info.keys())[:5]:  # Show first 5
        print(f"  {key}: {cal_info[key]}")
