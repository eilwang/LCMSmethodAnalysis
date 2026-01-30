"""Test AnnData display during loading."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from diann_collection import DiannCollection

zip_path = "/Users/eileen.wang/Desktop/diann/SampleData/BPS/5bb65d07aa6a2f77f81b5e08ab034d2b.zip"

print("Testing AnnData display during loading...")
print("=" * 80)

# Load just one level to see the output
with DiannCollection() as collection:
    collection.add_from_zip(
        zip_path,
        levels=['gene'],  # Just gene to keep output manageable
        search_type='bps',
        strict=False
    )

    print("\n" + "=" * 80)
    print("Final collection:")
    print("=" * 80)
    gene_data = collection['gene']
    print(gene_data)
