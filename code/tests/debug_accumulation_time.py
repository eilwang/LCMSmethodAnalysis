"""
Debug script for checking IMS Accumulation Time parsing.

Usage: python debug_accumulation_time.py <path_to_method>
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from bruker_method import BrukerMethod
from method_path_resolver import MethodPathResolver


def debug_accumulation_time(method_path: str):
    """Debug accumulation time parsing for a given method."""
    print("=" * 80)
    print("ACCUMULATION TIME DEBUG")
    print("=" * 80)
    print(f"Method: {method_path}\n")

    # Parse with BrukerMethod
    try:
        method = BrukerMethod(method_path)
        acc_time = method.get_param('IMS_Service_AccumulationTime')
        print(f"✓ Parsed IMS_Service_AccumulationTime: {acc_time} ms")
    except Exception as e:
        print(f"✗ Error parsing method: {e}")
        return

    # Now check the raw XML to see what's there
    print("\n" + "=" * 80)
    print("RAW XML INSPECTION")
    print("=" * 80)

    # Resolve method path
    resolver = MethodPathResolver(method_path)
    try:
        method_dir = resolver.resolve()
        xml_path = method_dir / 'microTOFQImpacTemAcquisition.method'

        if not xml_path.exists():
            print(f"✗ XML file not found: {xml_path}")
            return

        # Parse XML
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # Search for all accumulation time parameters
        print("\nSearching for all parameters containing 'Accumulation'...\n")

        found_any = False

        # Check in instrument section
        instrument_elem = root.find('.//instrument/qtofimpactemacq')
        if instrument_elem is not None:
            print("In <instrument><qtofimpactemacq>:")
            for elem in instrument_elem.iter():
                if elem.tag.startswith('para_') and 'permname' in elem.attrib:
                    permname = elem.attrib['permname']
                    if 'accumulation' in permname.lower():
                        value = elem.attrib.get('value', 'N/A')
                        print(f"  {permname} = {value}")
                        found_any = True

        # Check in method/qtofimpactemacq/timetable/segment
        method_elem = root.find('.//method/qtofimpactemacq')
        if method_elem is not None:
            timetable_elem = method_elem.find('timetable')
            if timetable_elem is not None:
                segments = timetable_elem.findall('segment')
                print(f"\nIn <method><qtofimpactemacq><timetable> ({len(segments)} segment(s)):")

                for i, segment in enumerate(segments):
                    endtime = segment.attrib.get('endtime', 'N/A')
                    print(f"  Segment {i} (endtime={endtime}):")

                    for elem in segment:
                        if elem.tag.startswith('para_') and 'permname' in elem.attrib:
                            permname = elem.attrib['permname']
                            if 'accumulation' in permname.lower():
                                value = elem.attrib.get('value', 'N/A')
                                print(f"    {permname} = {value}")
                                found_any = True

        # Check in polarity configs
        print("\nIn polarity configurations:")
        for polarity_elem in root.findall('.//PolarityEntry'):
            polarity_name = polarity_elem.attrib.get('name', 'unknown')

            for source_elem in polarity_elem.findall('.//IonSourceEntry'):
                source_name = source_elem.attrib.get('name', 'unknown')

                for elem in source_elem.iter():
                    if elem.tag.startswith('para_') and 'permname' in elem.attrib:
                        permname = elem.attrib['permname']
                        if 'accumulation' in permname.lower():
                            value = elem.attrib.get('value', 'N/A')
                            print(f"  [{polarity_name}/{source_name}] {permname} = {value}")
                            found_any = True

        if not found_any:
            print("  No parameters containing 'Accumulation' found in XML")

        # Summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        if acc_time is not None:
            print(f"✓ Successfully parsed: {acc_time} ms")
        else:
            print("✗ Accumulation time not found in parsed parameters")
            print("\nPossible reasons:")
            print("  1. Parameter is in a different XML location not covered by parser")
            print("  2. Parameter has a different name")
            print("  3. Method file structure is different from expected")
            print("\nPlease check the 'RAW XML INSPECTION' section above to see")
            print("where the parameter is located in the XML file.")

    finally:
        resolver.cleanup()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_accumulation_time.py <path_to_method>")
        print("\nExample:")
        print("  python debug_accumulation_time.py /path/to/DIA003.proteoscape.m")
        print("  python debug_accumulation_time.py /path/to/DIA011RT70.m.zip")
        sys.exit(1)

    method_path = sys.argv[1]
    debug_accumulation_time(method_path)
