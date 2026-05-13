# adapted from https://github.com/nickdelgrosso/XCaliburMethodReader
import numpy as np
import pandas as pd
import re
from typing import Optional, Union
from pathlib import Path
import olefile
import copy
import warnings

from ..method_path_resolver import MethodPathResolver

# Import for pressure trace extraction (handle gracefully if not available)
try:
    from .extractor.raw_extractor_dotnet import extract_raw
    RAW_EXTRACTION_AVAILABLE = True
except ImportError:
    RAW_EXTRACTION_AVAILABLE = False
    warnings.warn("Raw file extraction not available - install extractor dependencies to use pressure traces")

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
    
    def copy(self):
        return copy.deepcopy(self)
    
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

            elif key == 'Neo.PumpModule.Pump.StartColumnWash':
                gradient_step[key] = True

        sections['Instrument Setup'] = sections.pop('initial     Instrument Setup')
        # Look for Equilibration section with any time prefix
        equil_key = [k for k in sections.keys() if 'Equilibration' in k][0]
        equil_df = pd.DataFrame([sections.pop(equil_key)])

        # Convert gradient list to DataFrame
        gradient_df = pd.DataFrame(sections['Gradient'])

        # Convert numeric columns to float (skip non-numeric like 'Curve')
        for col in gradient_df.columns:
            gradient_df[col] = pd.to_numeric(gradient_df[col])
        
        # get the length of a step
        gradient_df['length [min]'] = gradient_df['time [min]'].diff().fillna(0)

        for col in equil_df.columns:
            equil_df[col] = pd.to_numeric(equil_df[col])

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


    def adjusted_elution(self, 
                         in_place: bool = False,
                         dead_time: Optional[float] = None,
                         dead_volume: Optional[float] = None,
                         direct_only: Optional[float] = None,
                         default_shift: float = 0,
                         extrapolate_points: Optional[list] = None,
                         raw_file_path: Optional[str] = None,
                         pressure_time_ranges: Optional[list] = None,
                         pressure_to_flow_ratio: Optional[float] = None,
                         use_real_composition: bool = False
                         ) -> Union[None, "VNeoMethod"]:
        """
        Adjust elution times based on dead volume/time with trap column support.
        Optionally use actual pressure traces from raw files to determine flow rates.
        
        Parameters:
        -----------
        in_place : bool
            Whether to modify the current object or return a copy
        dead_time : float, optional
            Dead time in minutes
        dead_volume : float, optional  
            Dead volume in nL (includes trap column if applicable)
        direct_only : float, optional
            Direct injection dead volume in nL (bypass trap column)
        default_shift : float
            Default shift to use if no dead_time/volume provided
        extrapolate_points : list of dict, optional
            Additional gradient points to add at end. Each dict should contain:
            {'time': float, 'b_percent': float, 'flow_rate': float}
            where 'time' is the length/duration of the interval (not absolute time)
        raw_file_path : str, optional
            Path to raw file to extract pressure traces from
        pressure_time_ranges : list of dict, optional
            Time ranges to use pressure traces for flow rate calculation. Each dict should contain:
            {'start_time': float, 'end_time': float, 'method_time_start': float, 'method_time_end': float}
            where start_time/end_time are in the raw file time scale, 
            and method_time_start/method_time_end are in the method time scale
        pressure_to_flow_ratio : float, optional
            Ratio to convert pressure (bar) to flow rate (µL/min). 
            Flow rate = pressure * ratio
        use_real_composition : bool, optional
            If True, extract real %B composition from raw file and create adjusted %B column.
            Uses the same time ranges as pressure_time_ranges for composition adjustments
        """

        # How much volume is pushed through the column at the RT of the first peptide that elutes
        # Essentially dead volume of the LC system

        if in_place == False:
            copied = self.copy()
            gradient = copied.gradient

        else:
            gradient = self.gradient
            
        # Process pressure traces from raw file if provided
        original_flow_rates = gradient['Neo.PumpModule.Pump.Flow.Nominal [µl/min]'].copy()  # Store original before pressure corrections
        
        # Initialize real %B composition column if requested
        if use_real_composition:
            gradient['Real %B Composition [%]'] = gradient['Neo.PumpModule.Pump.%B.Value [%]'].copy()
        
        if raw_file_path and pressure_time_ranges and (pressure_to_flow_ratio or use_real_composition):
            if not RAW_EXTRACTION_AVAILABLE:
                warnings.warn("Raw file extraction not available - skipping pressure trace processing")
            else:
                try:
                    print(f"Extracting {'pressure and composition' if use_real_composition else 'pressure'} traces from: {raw_file_path}")
                    raw_data = extract_raw(raw_file_path)
                    
                    # Apply pressure-derived flow rates and/or real composition to specified time ranges
                    for time_range in pressure_time_ranges:
                        raw_start = time_range['start_time']
                        raw_end = time_range['end_time'] 
                        method_start = time_range['method_time_start']
                        method_end = time_range['method_time_end']
                        
                        # Extract raw data for the specified time range
                        data_mask = (raw_data['time_min'] >= raw_start) & (raw_data['time_min'] <= raw_end)
                        data_subset = raw_data[data_mask]
                        
                        if len(data_subset) > 0:
                            method_mask = (gradient['time [min]'] >= method_start) & (gradient['time [min]'] <= method_end)
                            
                            # Process pressure data if ratio provided
                            if pressure_to_flow_ratio:
                                avg_pressure = data_subset['AnalyticalPumpPressureInBar'].mean()
                                derived_flow_rate = avg_pressure * pressure_to_flow_ratio
                                
                                print(f"Time range {raw_start:.1f}-{raw_end:.1f} min (raw): avg pressure = {avg_pressure:.0f} bar")
                                print(f"  -> derived flow rate = {derived_flow_rate:.3f} µL/min")
                                print(f"  -> applying to method time {method_start:.1f}-{method_end:.1f} min")
                                
                                gradient.loc[method_mask, 'Neo.PumpModule.Pump.Flow.Nominal [µl/min]'] = derived_flow_rate
                            
                            # Process composition data if requested
                            if use_real_composition and 'PercentBComposition' in data_subset.columns:
                                avg_composition = data_subset['PercentBComposition'].mean()
                                
                                print(f"Time range {raw_start:.1f}-{raw_end:.1f} min (raw): avg %B composition = {avg_composition:.1f}%")
                                print(f"  -> applying real %B to method time {method_start:.1f}-{method_end:.1f} min")
                                
                                gradient.loc[method_mask, 'Real %B Composition [%]'] = avg_composition
                            elif use_real_composition:
                                warnings.warn(f"PercentBComposition column not found in raw data for time range {raw_start}-{raw_end} min")
                        else:
                            warnings.warn(f"No raw data found in time range {raw_start}-{raw_end} min")
                            
                except Exception as e:
                    warnings.warn(f"Error processing pressure traces: {e}")
            
        # Recalculate length intervals after potential flow rate modifications
        if len(gradient) > 1:
            gradient['length [min]'] = gradient['time [min]'].diff()
            gradient.iloc[0, gradient.columns.get_loc('length [min]')] = gradient.iloc[0]['time [min]']
            
        # Calculate volumes using ORIGINAL flow rates to maintain consistent volume progression
        gradient['volume (nL)'] = gradient['length [min]'] * original_flow_rates * 1000  # convert to nL
        gradient['total volume (nL)'] = gradient['volume (nL)'].cumsum()

        # Add extrapolation points if provided
        if extrapolate_points:
            final_total_volume = gradient['total volume (nL)'].iloc[-1]
            current_time = gradient['time [min]'].iloc[-1]
            
            # Create list to store new rows 
            new_rows = []
            
            for point in extrapolate_points:
                length_min = point['time']  # 'time' now represents interval length
                b_percent = point['b_percent']
                flow_rate = point['flow_rate']
                
                # Calculate new absolute time
                new_time = current_time + length_min
                
                # Calculate volume for this segment
                volume_nl = length_min * flow_rate * 1000  # convert to nL
                total_volume_nl = final_total_volume + volume_nl
                
                # Create new row with same structure as original gradient
                new_row = gradient.iloc[-1].copy()  # Copy last row to maintain structure
                
                # Update the relevant values
                new_row['time [min]'] = new_time
                new_row['Neo.PumpModule.Pump.%B.Value [%]'] = b_percent
                new_row['Neo.PumpModule.Pump.Flow.Nominal [µl/min]'] = flow_rate
                new_row['length [min]'] = length_min
                new_row['volume (nL)'] = volume_nl
                new_row['total volume (nL)'] = total_volume_nl
                
                # Reset any trap column specific columns to default values
                if 'Neo.PumpModule.Pump.StartColumnWash' in new_row.index:
                    new_row['Neo.PumpModule.Pump.StartColumnWash'] = False
                
                new_rows.append(new_row)
                
                # Update for next iteration
                final_total_volume = total_volume_nl
                current_time = new_time
            
            # Append all new rows at once
            if new_rows:
                new_df = pd.DataFrame(new_rows)
                gradient = pd.concat([gradient, new_df], ignore_index=True)
        
        # Update the object's gradient with the potentially extended gradient
        if in_place == False:
            copied.gradient = gradient
        else:
            self.gradient = gradient

        if not dead_volume:
            if not dead_time:
                warnings.warn(f'dead time not supplied. Using RT shift of {default_shift} instead')
                dead_time = default_shift

            dead_volume = np.interp(dead_time, gradient['time [min]'], gradient['total volume (nL)'])

        # Check for trap column scenario with "Neo.PumpModule.Pump.StartColumnWash" 
        has_column_wash = 'Neo.PumpModule.Pump.StartColumnWash' in gradient.columns
        
        if has_column_wash and direct_only is not None:
            # Find the column wash switch point
            column_wash_mask = gradient['Neo.PumpModule.Pump.StartColumnWash'].fillna(0).astype(bool)
            wash_start_idx = None
            
            if column_wash_mask.any():
                wash_start_idx = column_wash_mask.idxmax()  # First True value
                wash_start_time = gradient.loc[wash_start_idx, 'time [min]']
                wash_start_volume = gradient.loc[wash_start_idx, 'total volume (nL)']
                
                # print(f"Column wash starts at {wash_start_time:.1f} min (volume: {wash_start_volume:.0f} nL)")
                # print(f"Dead volume (trap): {dead_volume:.0f} nL")
                # print(f"Dead volume (direct): {direct_only:.0f} nL")
                
                # Calculate volume difference that gets "lost" when switching from trap to direct
                trapped_volume = dead_volume - direct_only
                print(f"Trapped volume: {trapped_volume:.0f} nL")
                
                # Calculate what %B gradient was in the trapped volume at wash start
                trapped_volume_start = wash_start_volume - trapped_volume
                trapped_volume_end = wash_start_volume
                
                # Find %B values that were in the trapped volume space
                trapped_b_values = []
                trapped_times = []
                
                for i, row in gradient.iterrows():
                    vol_with_dead = row['total volume (nL)'] + dead_volume
                    if trapped_volume_start <= vol_with_dead <= trapped_volume_end:
                        trapped_b_values.append(row['Neo.PumpModule.Pump.%B.Value [%]'])
                        trapped_times.append(row['time [min]'])
                
                print(f"Trapped %B range: {min(trapped_b_values):.1f}% to {max(trapped_b_values):.1f}%" if trapped_b_values else "Trapped %B range: N/A")
                
                # Initialize dead volume tracking
                gradient['Dead Volume Used (nL)'] = dead_volume
                gradient['Total + Dead Volume (nL)'] = gradient['total volume (nL)'] + dead_volume
                gradient['Trapped %B Contribution'] = 0.0  # Track delayed %B from trap
                
                # After column wash: new volume uses direct path, but trapped volume continues through trap path
                post_wash_mask = gradient.index >= wash_start_idx
                gradient.loc[post_wash_mask, 'Dead Volume Used (nL)'] = direct_only
                
                # For post-wash timepoints, calculate the effective volume that reaches the column
                # This includes: trapped volume (continues with trap timing) + new volume (direct timing)
                
                if post_wash_mask.any():
                    # Volume at wash start that was already in the trap path
                    wash_start_total_vol = wash_start_volume
                    
                    # For post-wash times: continue using trap dead volume until trapped volume is flushed out
                    # Then switch to direct dead volume for new volume
                    for idx in gradient[post_wash_mask].index:
                        current_base_vol = gradient.loc[idx, 'total volume (nL)']
                        new_vol_since_wash = current_base_vol - wash_start_total_vol
                        
                        # The trapped volume continues with full dead volume
                        # New volume since wash uses direct dead volume  
                        total_effective_vol = wash_start_volume + dead_volume + new_vol_since_wash + direct_only
                        gradient.loc[idx, 'Total + Dead Volume (nL)'] = total_effective_vol
                
                # Calculate when the trapped %B will elute through the direct path
                # The trapped volume takes additional time to traverse the direct path
                if trapped_b_values:
                    # Estimate flow rate for calculating delay
                    avg_flow = gradient['Neo.PumpModule.Pump.Flow.Nominal [µl/min]'].mean()
                    trapped_elution_delay = trapped_volume / (avg_flow * 1000 / 60)  # convert to minutes
                    
                    print(f"Trapped %B elution delay: {trapped_elution_delay:.2f} min")
                    
                    # Add trapped %B contribution to post-wash timepoints
                    for i in gradient[post_wash_mask].index:
                        current_time = gradient.loc[i, 'time [min]']
                        delayed_time = current_time - wash_start_time - trapped_elution_delay
                        
                        if delayed_time > 0 and trapped_b_values:
                            # Interpolate what %B from trapped volume is eluting now
                            if len(trapped_times) > 1:
                                trapped_b_now = np.interp(delayed_time, 
                                                         np.array(trapped_times) - min(trapped_times), 
                                                         trapped_b_values)
                            else:
                                trapped_b_now = trapped_b_values[0]
                            
                            gradient.loc[i, 'Trapped %B Contribution'] = trapped_b_now
                
        else:
            # Standard single dead volume calculation
            gradient['Dead Volume Used (nL)'] = dead_volume  
            gradient['Total + Dead Volume (nL)'] = gradient['total volume (nL)'] + dead_volume
            gradient['Trapped %B Contribution'] = 0.0
            
        # time it actually takes to elute the set %B through the end of the column, including dead volume
        # Use numerical integration to account for varying flow rates (important for pressure-corrected gradients)
        def calculate_actual_elution_time(target_volume_nl):
            """Calculate actual time to elute a given volume considering varying flow rates."""
            if target_volume_nl <= 0:
                return 0.0
            
            cumulative_time = 0.0
            cumulative_volume = 0.0
            
            for i in range(len(gradient)):
                if cumulative_volume >= target_volume_nl:
                    break
                    
                # Volume in this segment (based on original gradient)
                segment_volume = gradient.iloc[i]['volume (nL)']
                
                # How much volume do we still need to reach the target?
                remaining_volume = target_volume_nl - cumulative_volume
                
                # Actual flow rate during this segment (may be pressure-corrected)
                actual_flow_rate = gradient.iloc[i]['Neo.PumpModule.Pump.Flow.Nominal [µl/min]']
                
                if segment_volume >= remaining_volume:
                    # Target volume is reached within this segment
                    # Calculate time needed for remaining volume at actual flow rate
                    if actual_flow_rate > 0:
                        time_needed = remaining_volume / (actual_flow_rate * 1000)  # nL / (µL/min * 1000) = minutes
                        cumulative_time += time_needed
                    break
                else:
                    # Need to process this entire segment
                    if actual_flow_rate > 0:
                        segment_time = segment_volume / (actual_flow_rate * 1000)  # time to pump segment volume at actual flow rate (minutes)
                        cumulative_time += segment_time
                    else:
                        # Fallback to original segment duration if flow rate is zero
                        cumulative_time += gradient.iloc[i]['length [min]']
                    
                    cumulative_volume += segment_volume
            
            return cumulative_time
        
        gradient['Actual Time to Elute Nominal %B (min)'] = gradient['Total + Dead Volume (nL)'].apply(calculate_actual_elution_time)

        # Calculate actual %B including trapped contributions
        gradient['Base Actual %B'] = gradient['time [min]'].apply(lambda x: np.interp(x, gradient['Actual Time to Elute Nominal %B (min)'], gradient['Neo.PumpModule.Pump.%B.Value [%]']))
        
        # For trap column scenarios, add the trapped %B contribution
        if has_column_wash and direct_only is not None and 'Trapped %B Contribution' in gradient.columns:
            # Combine base %B with trapped %B (could use mixing models here)
            # Simple approach: weighted average or additive contribution
            # For now, use additive contribution with decay
            gradient['Actual %B'] = gradient['Base Actual %B'] + gradient['Trapped %B Contribution'] * 0.3  # 30% contribution factor
            # Ensure %B stays within 0-100% bounds
            gradient['Actual %B'] = gradient['Actual %B'].clip(0, 100)
        else:
            gradient['Actual %B'] = gradient['Base Actual %B']

        #   df['Nominal Elution Volume (nL)'] = np.interp(df['Rt'], gradient['Time (min)'], gradient['Total Volume (nL)'])
        #   # What %B a peptide theoretically elutes at assuming no dead volume
        #   df['Nominal Elution %B'] = np.interp(df['Rt'], gradient['Time (min)'], gradient['%B'])

        #   # What %B a peptide actually elutes at by subtracting the amount of time it takes for everything to pass through the system + column
        #   ## hmm should this actually only take into account the column volume? not the fully system volume?
        #   df['Actual Elution %B'] = np.interp(df['Rt'], gradient['Time (min)'], gradient['Actual %B'])

        if in_place == False:
            return copied
        
        return None


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
