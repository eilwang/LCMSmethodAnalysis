# adapted from https://github.com/nickdelgrosso/XCaliburMethodReader
import pandas as pd
import re
from typing import Dict, List, Optional, Any
from pathlib import Path
import olefile

from ..method_path_resolver import MethodPathResolver

class VNeoMethod:
    """Parse and provide structured access to LC method parameters."""

    def __init__(self, meth_path: str):
        """
        Initialize with method file path.

        Parameters:
        -----------
        meth_path : str
            Path to .meth file or .zip file containing .meth file
        """
        self.original_path = Path(meth_path)

        # Create path resolver to handle both .meth files and zip archives
        self.resolver = MethodPathResolver(meth_path)

        # Resolve the path
        self.meth_path = self.resolver.resolve()

        # If original path was to a zip, find the .meth file inside
        if self.original_path.suffix == '.zip':
            # Look for .meth files in resolved directory
            meth_files = list(self.meth_path.glob('*.meth'))
            if meth_files:
                self.meth_path = meth_files[0]
            else:
                raise FileNotFoundError(f"No .meth file found in zip: {self.original_path}")

        self.runtime, self.params, self.gradient, self.equil = self._parse_method()

    def read_meth(self) -> str:
        methole = olefile.OleFileIO(str(self.meth_path))
        text = methole.openstream(['SiiXcalibur', 'Text']).read().decode('utf-16')
        methole.close()
        return text

    def get_keyvalue(self, line):
        """
        find out if a line has a key value pair, denoted by the prescence of a colon
        if so, split the line into key and value and return them
           * if the value has a unit attached in square brackets, append the unit to the key
        if not, return the line as key (which may be a sectionheader) and None as value
           * if the section header has a unit in brackets, strip it from the key

        :param self: Description
        :param line: Description
        """
        key_value_pair = re.search(': ', line)

        if key_value_pair:
            key, value = line.split(': ', 1)
            unit = re.search(r'\[.+?\]', value)
            if unit:
                key = f'{key} {unit.group(0)}'  # unit.group(0) now has no extra spaces
                value = value.replace(unit.group(0), '').strip()
            return key.strip(), value.strip()

        return line.strip(), None
    
    def _parse_method(self):
        raw_text = self.read_meth()
        lines = raw_text.split('\r\n')

        sections = {
            'Gradient': []  # Store as list of dicts, convert to DataFrame later
        }

        current_section = None
        gradient_step = {}

        for line in lines[1:]:
            if not line.strip():
                continue
            
            # Parse key-value pair once
            key, value = self.get_keyvalue(line)
            is_indented = line.startswith(' ')
            
            # Handle non-indented lines (section headers or top-level key-value pairs)
            if not is_indented:
                if value:  # Top-level key-value pair
                    sections[key] = value
                    current_section = key
                elif key == '0.000 [min] Run':  # Start gradient
                    current_section = 'Gradient'
                    gradient_step = {'time [min]': '0.000'}
                elif current_section == 'Gradient':  # Gradient time point or end
                    sections['Gradient'].append(gradient_step)
                    if 'Stop Run' not in key:
                        # Extract just the numeric time value, stripping [min] unit if present
                        time_value = re.sub(r'\s*\[min\]', '', key)
                        gradient_step = {'time [min]': time_value}
                    else:
                        current_section = key
                else:  # Regular section header
                    current_section = key
            
            # Handle indented lines (section content)
            elif value and current_section:
                if current_section == 'Gradient':
                    gradient_step[key] = value
                else:
                    if current_section not in sections:
                        sections[current_section] = {} # type: ignore
                    sections[current_section][key] = value

        sections['Instrument Setup'] = sections.pop('initial     Instrument Setup')
        # Look for Equilibration section with any time prefix
        equil_key = [k for k in sections.keys() if 'Equilibration' in k][0]
        equil_df = pd.DataFrame([sections.pop(equil_key)])

        # Convert gradient list to DataFrame
        gradient_df = pd.DataFrame(sections['Gradient'])

        # Convert numeric columns to float (skip non-numeric like 'Curve')
        for col in gradient_df.columns:
            gradient_df[col] = pd.to_numeric(gradient_df[col], errors='ignore')

        for col in equil_df.columns:
            equil_df[col] = pd.to_numeric(equil_df[col], errors='ignore')

        return float(sections['Run time [min]']), sections['Instrument Setup'], gradient_df, equil_df

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




#     def get_gradient_at_time(self, time: float, column: str = '%B') -> Optional[float]:
#         """
#         Get gradient value at specific time (with linear interpolation).

#         Parameters:
#         -----------
#         time : float
#             Time point
#         column : str
#             Column name (e.g., '%B', '%A')

#         Returns:
#         --------
#         float or None
#             Interpolated value or None if gradient not available
#         """
#         if self.gradient is None or column not in self.gradient.columns:
#             return None

#         # Linear interpolation
#         times = self.gradient['Time'].values
#         values = self.gradient[column].values

#         if time <= times[0]:
#             return values[0]
#         if time >= times[-1]:
#             return values[-1]

#         # Find surrounding points
#         for i in range(len(times) - 1):
#             if times[i] <= time <= times[i + 1]:
#                 # Linear interpolation
#                 t1, t2 = times[i], times[i + 1]
#                 v1, v2 = values[i], values[i + 1]
#                 return v1 + (v2 - v1) * (time - t1) / (t2 - t1)

#         return None

#     def summary(self) -> str:
#         """Return summary of method."""
#         summary_lines = []
#         summary_lines.append("LC Method Summary")
#         summary_lines.append("=" * 50)

#         # Key parameters
#         if self.params:
#             summary_lines.append("\nKey Parameters:")
#             for key, value in list(self.params.items())[:10]:  # First 10
#                 summary_lines.append(f"  {key}: {value.get('raw')}")

#         # Gradient info
#         if self.gradient is not None:
#             summary_lines.append(f"\nGradient: {len(self.gradient)} time points")
#             summary_lines.append(f"Duration: {self.gradient['Time'].min():.1f} - {self.gradient['Time'].max():.1f} min")

#         # Sections
#         if self.sections:
#             summary_lines.append(f"\nSections: {len(self.sections)}")
#             for section in list(self.sections.keys())[:5]:  # First 5
#                 summary_lines.append(f"  - {section}")

#         return '\n'.join(summary_lines)

#     def __repr__(self):
#         return f"VNeoMethod(params={len(self.params)}, gradient={'Yes' if self.gradient is not None else 'No'})"


# # Usage example
# if __name__ == "__main__":
#     # Example usage
#     sample_text = """
#     Flow Rate: 0.3 mL/min
#     Column Temperature: 40 C

#     Gradient Table:
#     Time    %A    %B    Flow
#     0.0     95    5     0.3
#     10.0    60    40    0.3
#     20.0    5     95    0.3
#     25.0    5     95    0.3
#     """

#     method = VNeoMethod(sample_text)
#     print(method.summary())
#     print(f"\nFlow Rate: {method.get_param('Flow Rate')}")
#     print(f"\nGradient at 15 min: {method.get_gradient_at_time(15, '%B')}%")
#     print(f"\nGradient table:\n{method.gradient}")
