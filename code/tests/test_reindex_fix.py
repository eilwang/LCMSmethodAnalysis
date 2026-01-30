"""Quick test to verify reindexing fix."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from diann_collection import DiannCollection
import zipfile
import tempfile

zip_path = "/Users/eileen.wang/Desktop/diann/SampleData/BPS/5bb65d07aa6a2f77f81b5e08ab034d2b.zip"

# Extract first two folders
temp_dir = tempfile.mkdtemp()
with zipfile.ZipFile(zip_path, 'r') as zf:
    zf.extractall(temp_dir)

temp_path = Path(temp_dir)
processing_run = temp_path / "processing-run"
uuid_folders = [f for f in processing_run.iterdir() if f.is_dir()][:2]

print("Testing InvalidIndexError Fix")
print("=" * 80)

try:
    collection = DiannCollection()

    print("\n1. Loading first sample...")
    collection.add_single_search(
        str(uuid_folders[0]),
        sample_name="s1",
        levels=['precursor', 'protein'],  # Test with protein level
        search_type='bps'
    )

    protein_data = collection['protein']
    print(f"   Protein shape: {protein_data.shape}")
    print(f"   Obs index unique: {protein_data.obs_names.is_unique}")

    print("\n2. Loading second sample...")
    collection.add_single_search(
        str(uuid_folders[1]),
        sample_name="s2",
        levels=['precursor', 'protein'],
        search_type='bps'
    )

    protein_data = collection['protein']
    print(f"   Protein shape: {protein_data.shape}")
    print(f"   Obs index unique: {protein_data.obs_names.is_unique}")

    print(f"\n{'='*80}")
    print("✓✓✓ SUCCESS - No InvalidIndexError!")
    print(f"{'='*80}")

except Exception as e:
    print(f"\n{'='*80}")
    print(f"✗✗✗ ERROR: {type(e).__name__}")
    print(f"{'='*80}")
    print(f"{e}")
    import traceback
    traceback.print_exc()
