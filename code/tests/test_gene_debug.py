"""Debug gene level loading."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from anndiannloader import DiannLoader
import pandas as pd

# Load one sample and try gene level
loader = DiannLoader()

# Use the extracted file from temp
import zipfile
import tempfile

zip_path = "/Users/eileen.wang/Desktop/diann/SampleData/BPS/5bb65d07aa6a2f77f81b5e08ab034d2b.zip"

# Extract main zip
temp_dir = tempfile.mkdtemp()
with zipfile.ZipFile(zip_path, 'r') as zf:
    zf.extractall(temp_dir)

# Find first tims-diann.result.zip
from pathlib import Path
temp_path = Path(temp_dir)
first_zip = list(temp_path.rglob("*tims-diann.result.zip"))[0]

# Extract nested zip
nested_temp = tempfile.mkdtemp()
with zipfile.ZipFile(first_zip, 'r') as zf:
    zf.extractall(nested_temp)

# Find results.tsv
results_tsv = list(Path(nested_temp).rglob("results.tsv"))[0]

print(f"Loading from: {results_tsv}")

# Try to load gene level with error details
try:
    adata = loader.load_to_adata(str(results_tsv), level='gene', strict=False)
    print(f"✓ Success! Shape: {adata.shape}")
except Exception as e:
    print(f"✗ Failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
