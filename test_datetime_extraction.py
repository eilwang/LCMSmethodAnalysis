#!/usr/bin/env python3
"""
Test script to extract creation and finished datetime from .raw files
"""
import glob
from src.parsers.vneometh.extractor.raw_extractor_dotnet import extract_datetime

# Find a .raw file to test with
raw_files = glob.glob("data/**/*.raw", recursive=True)

if raw_files:
    test_file = raw_files[0]
    print(f"Testing datetime extraction with: {test_file}\n")
    
    try:
        datetime_info = extract_datetime(test_file)
        
        print("Extracted datetime information:")
        print(f"  Creation Date:  {datetime_info['creation_date']}")
        print(f"  Start Time:     {datetime_info['start_time']}")
        print(f"  End Time:       {datetime_info['end_time']}")
        
        # Calculate duration if needed
        from datetime import datetime
        start = datetime.strptime(datetime_info['start_time'], '%Y-%m-%d %H:%M:%S')
        end = datetime.strptime(datetime_info['end_time'], '%Y-%m-%d %H:%M:%S')
        duration = end - start
        print(f"\n  Duration:       {duration}")
        
    except Exception as e:
        print(f"Error: {e}")
else:
    print("No .raw files found in data directory")
    print("\nUsage example:")
    print("  from src.parsers.vneometh.extractor.raw_extractor_dotnet import extract_datetime")
    print("  datetime_info = extract_datetime('/path/to/file.raw')")
    print("  print(datetime_info)")
