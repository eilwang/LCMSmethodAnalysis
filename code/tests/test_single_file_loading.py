"""Test loading single files into DiannCollection."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from diann_collection import DiannCollection
import zipfile
import tempfile

# Extract one sample file to test single file loading
zip_path = "/Users/eileen.wang/Desktop/diann/SampleData/BPS/5bb65d07aa6a2f77f81b5e08ab034d2b.zip"

print("Extracting test files...")
print("=" * 80)

# Extract main zip
temp_dir = tempfile.mkdtemp()
with zipfile.ZipFile(zip_path, 'r') as zf:
    zf.extractall(temp_dir)

# Find first two tims-diann.result.zip files
temp_path = Path(temp_dir)
zip_files = list(temp_path.rglob("*tims-diann.result.zip"))[:2]

# Extract nested zips to get results.tsv files
test_files = []
for zip_file in zip_files:
    nested_temp = tempfile.mkdtemp()
    with zipfile.ZipFile(zip_file, 'r') as zf:
        zf.extractall(nested_temp)
    results_tsv = list(Path(nested_temp).rglob("results.tsv"))[0]
    test_files.append(results_tsv)
    print(f"Extracted: {results_tsv}")

print(f"\nFound {len(test_files)} test files")

# Test loading single files
print("\n" + "=" * 80)
print("Testing Single File Loading")
print("=" * 80)

with DiannCollection() as collection:
    # Load first file
    print("\n1. Loading first file...")
    collection.add_from_file(
        str(test_files[0]),
        sample_name="sample_1",
        levels=['gene']
    )

    # Load second file
    print("\n2. Loading second file...")
    collection.add_from_file(
        str(test_files[1]),
        sample_name="sample_2",
        levels=['gene']
    )

    # Show final collection
    print("\n" + "=" * 80)
    print("Final Collection")
    print("=" * 80)
    gene_data = collection['gene']
    print(f"\nGene level shape: {gene_data.shape}")
    print(f"Samples: {sorted(gene_data.var['UUID'].unique())}")
    print(f"\n{gene_data}")

    # Test loading without sample name (uses filename)
    print("\n" + "=" * 80)
    print("3. Loading file without sample name (auto-detect)...")
    collection.add_from_file(
        str(test_files[0]),
        levels=['gene']
    )

    gene_data = collection['gene']
    print(f"\nGene level shape: {gene_data.shape}")
    print(f"Samples: {sorted(gene_data.var['UUID'].unique())}")

print("\n" + "=" * 80)
print("✓ Single file loading test complete!")
print("=" * 80)
