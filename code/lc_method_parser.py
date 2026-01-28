import pandas as pd
import re
from typing import Dict, List, Optional, Any
import pandas as pd

class LCMethod:
    """Parse and provide structured access to LC method parameters."""

    def __init__(self, text: str):
        """
        Initialize with method text.

        Parameters:
        -----------
        text : str
            Raw method text from .meth file
        """
        self.raw_text = text
        self.params = self._parse_params(text)
        self.gradient = self._parse_gradient(text)
        self.sections = self._parse_sections(text)

    def _parse_sections(self, text: str) -> Dict[str, List[str]]:
        """Parse text into sections."""
        lines = text.split('\n')
        sections = {}
        current_section = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Detect section headers (lines ending with colon or containing certain keywords)
            if (line.endswith(':') or
                any(keyword in line.lower() for keyword in ['pump', 'column', 'autosampler', 'gradient'])):
                current_section = line
                sections[current_section] = []
            elif current_section:
                sections[current_section].append(line)

        return sections

    def _parse_params(self, text: str) -> Dict[str, Any]:
        """
        Parse method parameters into dictionary.

        Returns:
        --------
        Dict[str, Any]
            Dictionary of parameter names to values
        """
        params = {}

        # Pattern for key-value pairs (e.g., "Flow Rate: 0.3 mL/min")
        pattern = r'^([^:]+?):\s*([^\n]+?)$'

        for line in text.split('\n'):
            line = line.strip()
            match = re.match(pattern, line)
            if match:
                key = match.group(1).strip()
                value = match.group(2).strip()

                params[key] = value

        return params

    def _parse_gradient(self, text: str) -> Optional[pd.DataFrame]:
        """
        Parse LC gradient table into DataFrame.

        Returns:
        --------
        pd.DataFrame or None
            DataFrame with gradient time points, or None if not found
        """
        lines = text.split('\n')

        # Find gradient table section
        gradient_lines = []
        in_gradient = False
        header_found = False
        columns = []

        for line in lines:
            line_lower = line.lower()

            # Detect gradient table start
            if not in_gradient and ('gradient' in line_lower or 'time' in line_lower):
                in_gradient = True

                # Try to extract column names
                if 'time' in line_lower:
                    # Common patterns: "Time", "%A", "%B", "Flow", etc.
                    col_pattern = r'(Time|%[AB]|Flow|Curve)'
                    columns = re.findall(col_pattern, line, re.IGNORECASE)
                    header_found = True
                    continue

            # Parse gradient rows
            if in_gradient and line.strip():
                # Look for lines with multiple numbers
                numbers = re.findall(r'[\d.]+', line)
                if len(numbers) >= 2:  # At least time and one percentage
                    gradient_lines.append([float(n) for n in numbers])
                elif not numbers and gradient_lines:
                    # Empty line after data, stop parsing
                    break

        # Create DataFrame
        if gradient_lines:
            # Default column names if not found
            if not columns:
                num_cols = len(gradient_lines[0])
                if num_cols == 2:
                    columns = ['Time', '%B']
                elif num_cols == 3:
                    columns = ['Time', '%A', '%B']
                elif num_cols == 4:
                    columns = ['Time', '%A', '%B', 'Flow']
                else:
                    columns = [f'Col{i}' for i in range(num_cols)]

            # Ensure we have the right number of columns
            num_cols = len(gradient_lines[0])
            if len(columns) != num_cols:
                columns = columns[:num_cols] + [f'Col{i}' for i in range(len(columns), num_cols)]

            df = pd.DataFrame(gradient_lines, columns=columns[:num_cols])
            return df

        return None

    @property
    def params_df(self) -> pd.DataFrame:
        """
        Get parameters as a DataFrame.

        Returns:
        --------
        pd.DataFrame
            DataFrame with parameters as rows
        """
        if not self.params:
            return pd.DataFrame(columns=['Parameter', 'Value'])

        data = [{'Parameter': key, 'Value': value} for key, value in self.params.items()]
        df = pd.DataFrame(data)
        df.set_index('Parameter', inplace=True)
        return df

    def get_param(self, key: str) -> Optional[Any]:
        """
        Get parameter value by key.

        Parameters:
        -----------
        key : str
            Parameter name

        Returns:
        --------
        Value or None if not found
        """
        param = self.params.get(key)

        if param is not None:
            return param
        return None

    def get_section(self, section_name: str) -> Optional[List[str]]:
        """
        Get section content by name.

        Parameters:
        -----------
        section_name : str
            Section name

        Returns:
        --------
        List[str] or None
            Section lines or None if not found
        """
        return self.sections.get(section_name)

    def get_gradient_at_time(self, time: float, column: str = '%B') -> Optional[float]:
        """
        Get gradient value at specific time (with linear interpolation).

        Parameters:
        -----------
        time : float
            Time point
        column : str
            Column name (e.g., '%B', '%A')

        Returns:
        --------
        float or None
            Interpolated value or None if gradient not available
        """
        if self.gradient is None or column not in self.gradient.columns:
            return None

        # Linear interpolation
        times = self.gradient['Time'].values
        values = self.gradient[column].values

        if time <= times[0]:
            return values[0]
        if time >= times[-1]:
            return values[-1]

        # Find surrounding points
        for i in range(len(times) - 1):
            if times[i] <= time <= times[i + 1]:
                # Linear interpolation
                t1, t2 = times[i], times[i + 1]
                v1, v2 = values[i], values[i + 1]
                return v1 + (v2 - v1) * (time - t1) / (t2 - t1)

        return None

    def summary(self) -> str:
        """Return summary of method."""
        summary_lines = []
        summary_lines.append("LC Method Summary")
        summary_lines.append("=" * 50)

        # Key parameters
        if self.params:
            summary_lines.append("\nKey Parameters:")
            for key, value in list(self.params.items())[:10]:  # First 10
                summary_lines.append(f"  {key}: {value.get('raw')}")

        # Gradient info
        if self.gradient is not None:
            summary_lines.append(f"\nGradient: {len(self.gradient)} time points")
            summary_lines.append(f"Duration: {self.gradient['Time'].min():.1f} - {self.gradient['Time'].max():.1f} min")

        # Sections
        if self.sections:
            summary_lines.append(f"\nSections: {len(self.sections)}")
            for section in list(self.sections.keys())[:5]:  # First 5
                summary_lines.append(f"  - {section}")

        return '\n'.join(summary_lines)

    def __repr__(self):
        return f"LCMethod(params={len(self.params)}, gradient={'Yes' if self.gradient is not None else 'No'})"


# Usage example
if __name__ == "__main__":
    # Example usage
    sample_text = """
    Flow Rate: 0.3 mL/min
    Column Temperature: 40 C

    Gradient Table:
    Time    %A    %B    Flow
    0.0     95    5     0.3
    10.0    60    40    0.3
    20.0    5     95    0.3
    25.0    5     95    0.3
    """

    method = LCMethod(sample_text)
    print(method.summary())
    print(f"\nFlow Rate: {method.get_param('Flow Rate')}")
    print(f"\nGradient at 15 min: {method.get_gradient_at_time(15, '%B')}%")
    print(f"\nGradient table:\n{method.gradient}")
