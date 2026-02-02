"""Example demonstrating logging functionality in DiannCollection."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from diann_collection import DiannCollection

# Example 1: Create collection with logging to file
print("Example 1: Loading with log file")
print("=" * 80)

# Create collection with log file
log_path = "/Users/eileen.wang/Desktop/diann/code/diann_loading.log"
collection = DiannCollection(log_file=log_path)

# Load data (all output will be written to both stdout and log file)
data_folder = "/Users/eileen.wang/Desktop/diann/SampleData/BPS"
collection.add_from_folder(data_folder, search_type='bps')

# Explicitly close log file
collection.close_log()

print(f"\nLog file written to: {log_path}")
print(f"You can view it with: cat {log_path}")

print("\n" + "=" * 80)
print("Example 2: Loading without log file (stdout only)")
print("=" * 80)

# Create collection without log file (traditional behavior)
collection2 = DiannCollection()
# Output goes to stdout only
# collection2.add_from_folder(data_folder, search_type='bps')

print("\n" + "=" * 80)
print("Example 3: Using context manager (automatic cleanup)")
print("=" * 80)

# Using context manager automatically closes log file on exit
with DiannCollection(log_file="/Users/eileen.wang/Desktop/diann/code/diann_context.log") as collection3:
    # collection3.add_from_folder(data_folder, search_type='bps')
    pass

print("\nLog file automatically closed when exiting context manager")
