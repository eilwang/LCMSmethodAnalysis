"""Test loading single search folders into DiannCollection."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from diann_collection import DiannCollection
import zipfile
import tempfile

# Extract test folders from BPS zip
zip_path = "/Users/eileen.wang/Desktop/diann/SampleData/BPS/5bb65d07aa6a2f77f81b5e08ab034d2b.zip"

print("Extracting test folders...")
print("=" * 80)

# Extract main zip
temp_dir = tempfile.mkdtemp()
with zipfile.ZipFile(zip_path, 'r') as zf:
    zf.extractall(temp_dir)

# Find processing-run folder with UUID subfolders
temp_path = Path(temp_dir)
processing_run = temp_path / "processing-run"

# Get first two UUID folders (each contains tims-diann.result.zip)
uuid_folders = [f for f in processing_run.iterdir() if f.is_dir()][:2]

print(f"Found {len(uuid_folders)} test folders:")
for folder in uuid_folders:
    print(f"  - {folder.name}")

# Test loading single search folders
print("\n" + "=" * 80)
print("Testing Single Search Loading")
print("=" * 80)

with DiannCollection() as collection:
    # Load first search
    print("\n1. Loading first search folder...")
    collection.add_single_search(
        str(uuid_folders[0]),
        sample_name="search_1",
        levels=['gene'],
        search_type='bps'
    )

    # Load second search
    print("\n2. Loading second search folder...")
    collection.add_single_search(
        str(uuid_folders[1]),
        sample_name="search_2",
        levels=['gene'],
        search_type='bps'
    )

    # Show final collection
    print("\n" + "=" * 80)
    print("Final Collection")
    print("=" * 80)
    gene_data = collection['gene']
    print(f"\nGene level shape: {gene_data.shape}")
    print(f"Samples: {sorted(gene_data.var['UUID'].unique())}")
    print(f"\n{gene_data}")

    # Test loading without sample name (uses detected name)
    print("\n" + "=" * 80)
    print("3. Loading folder without sample name (auto-detect from folder)...")
    collection.add_single_search(
        str(uuid_folders[0]),
        levels=['gene'],
        search_type='bps'
    )

    gene_data = collection['gene']
    print(f"\nGene level shape: {gene_data.shape}")
    print(f"Samples: {sorted(gene_data.var['UUID'].unique())}")

print("\n" + "=" * 80)
print("✓ Single search loading test complete!")
print("=" * 80)
