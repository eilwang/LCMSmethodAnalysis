"""
Simple test for DiannCollection class using manually created AnnData objects
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from diann_collection import DiannCollection
import anndata as ad
import numpy as np
import pandas as pd
import tempfile


def create_mock_anndata(sample_name: str, n_obs: int = 3, n_vars: int = 5) -> ad.AnnData:
    """Create a mock AnnData object for testing."""
    X = np.random.rand(n_obs, n_vars)

    obs = pd.DataFrame({
        'Run': [f'{sample_name}_run{i}' for i in range(n_obs)],
        'Sample': [sample_name] * n_obs,
    }, index=[f'obs_{i}' for i in range(n_obs)])

    var = pd.DataFrame({
        'Modified.Sequence': [f'PEPTIDE{i}' for i in range(n_vars)],
        'Precursor.Id': [f'PEPTIDE{i}_2' for i in range(n_vars)],
    }, index=[f'var_{i}' for i in range(n_vars)])

    adata = ad.AnnData(X=X, obs=obs, var=var)
    adata.obs_names = [f'{sample_name}_{i}' for i in range(n_obs)]
    adata.var_names = [f'var_{i}' for i in range(n_vars)]

    return adata


def test_basic_collection():
    """Test basic collection operations with manually created AnnData."""
    print("=" * 80)
    print("TEST 1: BASIC COLLECTION OPERATIONS")
    print("=" * 80)

    collection = DiannCollection()

    # Manually add samples
    collection.data['sample1'] = {
        'precursor': create_mock_anndata('sample1', n_obs=3, n_vars=5),
        'protein': create_mock_anndata('sample1', n_obs=2, n_vars=3),
    }

    collection.data['sample2'] = {
        'precursor': create_mock_anndata('sample2', n_obs=4, n_vars=5),
    }

    # Test basic properties
    assert len(collection) == 2, "Should have 2 samples"
    assert 'sample1' in collection, "Should contain sample1"
    assert 'sample2' in collection, "Should contain sample2"

    # Test list methods
    samples = collection.list_samples()
    assert len(samples) == 2, "Should list 2 samples"
    assert 'sample1' in samples, "Should list sample1"
    assert 'sample2' in samples, "Should list sample2"

    levels_dict = collection.list_levels()
    assert 'sample1' in levels_dict, "Should have sample1 in levels dict"
    assert 'precursor' in levels_dict['sample1'], "sample1 should have precursor level"
    assert 'protein' in levels_dict['sample1'], "sample1 should have protein level"
    assert 'precursor' in levels_dict['sample2'], "sample2 should have precursor level"

    # Test access methods
    adata = collection['sample1', 'precursor']
    assert adata.shape == (3, 5), "Should have correct shape"

    # Access by sample name (get all levels)
    sample1_levels = collection['sample1']
    assert isinstance(sample1_levels, dict), "Should return dict"
    assert 'precursor' in sample1_levels, "Should have precursor"
    assert 'protein' in sample1_levels, "Should have protein"

    print("\n✓ Basic collection test passed")
    print(f"  Samples: {samples}")
    print(f"  Levels per sample: {levels_dict}")


def test_summary():
    """Test summary generation."""
    print("\n" + "=" * 80)
    print("TEST 2: SUMMARY GENERATION")
    print("=" * 80)

    collection = DiannCollection()

    collection.data['sample1'] = {
        'precursor': create_mock_anndata('sample1', n_obs=3, n_vars=5),
    }

    collection.data['sample2'] = {
        'precursor': create_mock_anndata('sample2', n_obs=4, n_vars=5),
    }

    # Generate summary
    summary = collection.summary_df()

    assert len(summary) == 2, "Summary should have 2 rows"
    assert 'Sample' in summary.columns, "Should have Sample column"
    assert 'precursor_shape' in summary.columns, "Should have shape columns"

    print("\n✓ Summary test passed")
    print("\nSummary DataFrame:")
    print(summary.to_string())


def test_save_load():
    """Test saving and loading collection."""
    print("\n" + "=" * 80)
    print("TEST 3: SAVE AND LOAD")
    print("=" * 80)

    # Create collection
    collection = DiannCollection()

    collection.data['sample1'] = {
        'precursor': create_mock_anndata('sample1', n_obs=3, n_vars=5),
    }

    collection.data['sample2'] = {
        'precursor': create_mock_anndata('sample2', n_obs=4, n_vars=5),
    }

    # Save
    temp_dir = tempfile.mkdtemp(prefix='diann_test_')
    save_path = Path(temp_dir) / "test_collection.pkl"

    try:
        collection.save(str(save_path))
        assert save_path.exists(), "Save file should exist"

        # Load collection
        loaded = DiannCollection.from_file(str(save_path))

        assert len(loaded) == 2, "Loaded collection should have 2 samples"
        assert len(loaded.list_samples()) == 2, "Should have 2 samples"
        assert 'sample1' in loaded, "Should have sample1"
        assert 'sample2' in loaded, "Should have sample2"

        # Check data integrity
        adata = loaded['sample1', 'precursor']
        assert adata.shape == (3, 5), "Should preserve shape"

        print("\n✓ Save/load test passed")
        print(f"  Saved and loaded {len(loaded)} samples")

    finally:
        import shutil
        shutil.rmtree(temp_dir)


def test_repr():
    """Test string representation."""
    print("\n" + "=" * 80)
    print("TEST 4: STRING REPRESENTATION")
    print("=" * 80)

    collection = DiannCollection()

    collection.data['sample1'] = {
        'precursor': create_mock_anndata('sample1', n_obs=3, n_vars=5),
        'protein': create_mock_anndata('sample1', n_obs=2, n_vars=3),
    }

    repr_str = repr(collection)
    assert 'DiannCollection' in repr_str, "Should contain class name"
    assert 'samples=1' in repr_str, "Should show number of samples"

    print("\n✓ String representation test passed")
    print(f"  Repr: {repr_str}")


# Run tests
if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("DIANN COLLECTION TESTS (SIMPLE)")
    print("=" * 80 + "\n")

    try:
        test_basic_collection()
        test_summary()
        test_save_load()
        test_repr()

        print("\n" + "=" * 80)
        print("✓ All tests passed!")
        print("=" * 80)

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
