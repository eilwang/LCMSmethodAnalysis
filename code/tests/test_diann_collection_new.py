"""
Test for DiannCollection class (new collection-based approach)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from diann_collection import DiannCollection
import tempfile
import zipfile
import pandas as pd


def create_mock_zip_structure():
    """
    Create a mock zip structure for testing.

    Creates:
    - temp_diann_tests.zip/
      ├── sample1-tims-diann.result.zip
      │   └── results.tsv
      └── sample2-tims-diann.result.zip
          └── results.tsv
    """
    # Create temp directory for test data
    temp_dir = tempfile.mkdtemp(prefix='diann_test_')
    temp_path = Path(temp_dir)

    # Create mock results.tsv data with all required columns for precursor level
    mock_data = pd.DataFrame({
        # Required for var_name, obs_name, x
        'Run': ['run1', 'run1', 'run1'],
        'Precursor.Id': ['PEPTIDEK_2', 'PROTEINR_2', 'SEQUENCEM_2'],
        'Precursor.Quantity': [1000.0, 2000.0, 1500.0],

        # Required for var section
        'File.Name': ['run1.d', 'run1.d', 'run1.d'],

        # Required for obs section
        'Protein.Group': ['P001', 'P002', 'P003'],
        'Protein.Ids': ['P001', 'P002', 'P003'],
        'Protein.Names': ['Protein1', 'Protein2', 'Protein3'],
        'Genes': ['GENE1', 'GENE2', 'GENE3'],
        'All Mapped Proteins': ['Protein1', 'Protein2', 'Protein3'],
        'All Mapped Genes': ['GENE1', 'GENE2', 'GENE3'],
        'Modified.Sequence': ['PEPTIDEK', 'PROTEINR', 'SEQUENCEM'],
        'Stripped.Sequence': ['PEPTIDEK', 'PROTEINR', 'SEQUENCEM'],
        'Precursor.Charge': [2, 2, 2],
        'Lib.Index': [0, 1, 2],

        # Add commonly used layers columns
        'Q.Value': [0.001, 0.002, 0.001],
        'RT': [10.5, 11.2, 12.1],
        'IM': [0.8, 0.85, 0.9],
        'iIM': [1.2, 1.3, 1.4],
        'Predicted.RT': [10.4, 11.1, 12.0],
        'Predicted.IM': [0.81, 0.86, 0.91],
        'Predicted.iIM': [1.21, 1.31, 1.41],
        'Precursor.Mz': [500.25, 600.30, 550.28],
        'iRT': [50.5, 55.2, 52.1],
        'Predicted.iRT': [50.4, 55.1, 52.0],
        'PEP': [0.0001, 0.0002, 0.0001],
        'Global.Q.Value': [0.001, 0.002, 0.001],
        'Proteotypic': [1, 1, 0],
        'Precursor.Normalised': [1100.0, 2100.0, 1600.0],
        'RT.Start': [10.0, 10.8, 11.5],
        'RT.Stop': [11.0, 11.6, 12.5],
        'Lib.Q.Value': [0.0001, 0.0002, 0.0001],
        'Ms1.Profile.Corr': [0.95, 0.93, 0.96],
        'Ms1.Area': [1000000.0, 2000000.0, 1500000.0],
        'Evidence': [5.2, 4.8, 5.5],
        'Spectrum.Similarity': [0.92, 0.89, 0.94],
        'Averagine': [0.85, 0.87, 0.86],
        'Mass.Evidence': [2, 2, 2],
        'CScore': [0.95, 0.93, 0.96],
        'Decoy.Evidence': [0.1, 0.2, 0.15],
        'Decoy.CScore': [0.05, 0.07, 0.06],
        'Fragment.Quant.Raw': [1000.0, 2000.0, 1500.0],
        'Fragment.Quant.Corrected': [1050.0, 2050.0, 1550.0],
        'Fragment.Correlations': [0.95, 0.93, 0.96],
        'MS2.Scan': [1001, 1002, 1003],
        'Fragment.Info': ['y3,y4,y5', 'y3,y4', 'y3,y4,y5,y6'],
        'Precursor.Translated': [1000.0, 2000.0, 1500.0],
        'Translated.Quality': [0.95, 0.93, 0.96],
        'Ms1.Translated': [1000.0, 2000.0, 1500.0],
        'Quantity.Quality': [0.95, 0.93, 0.96],
        'Translated.Q.Value': [0.001, 0.002, 0.001],

        # For protein level
        'PG.MaxLFQ': [5000.0, 6000.0, 5500.0],
        'PG.Quantity': [4800.0, 5800.0, 5300.0],
        'Protein.Q.Value': [0.001, 0.002, 0.001],

        # For gene level
        'Genes.MaxLFQ': [5000.0, 6000.0, 5500.0],
        'Genes.Quantity': [4800.0, 5800.0, 5300.0],
        'GG.Q.Value': [0.001, 0.002, 0.001],
    })

    # Create two sample zip files
    main_zip_path = temp_path / 'diann_searches.zip'

    with zipfile.ZipFile(main_zip_path, 'w') as main_zip:
        for sample_num in [1, 2]:
            # Create nested zip for each sample
            sample_zip_path = temp_path / f'sample{sample_num}-tims-diann.result.zip'

            with zipfile.ZipFile(sample_zip_path, 'w') as sample_zip:
                # Write results.tsv to nested zip
                results_tsv = temp_path / f'results{sample_num}.tsv'
                # Modify data slightly for each sample
                sample_data = mock_data.copy()
                sample_data['Run'] = f'run{sample_num}'
                sample_data['File.Name'] = f'run{sample_num}.d'
                sample_data['Precursor.Quantity'] = sample_data['Precursor.Quantity'] * sample_num
                sample_data.to_csv(results_tsv, sep='\t', index=False)

                # Add to nested zip
                sample_zip.write(results_tsv, 'results.tsv')
                results_tsv.unlink()  # Clean up temp file

            # Add nested zip to main zip
            main_zip.write(sample_zip_path, sample_zip_path.name)
            sample_zip_path.unlink()  # Clean up temp nested zip

    print(f"Created mock test data at: {main_zip_path}")
    return str(main_zip_path), temp_dir


def test_basic_collection():
    """Test basic collection operations."""
    print("=" * 80)
    print("TEST 1: BASIC COLLECTION OPERATIONS")
    print("=" * 80)

    zip_path, temp_dir = create_mock_zip_structure()

    try:
        with DiannCollection() as collection:
            # Load data
            collection.add_from_zip(zip_path, levels=['precursor'])

            # Test basic properties
            assert len(collection) == 2, "Should have 2 samples"
            assert 'sample1-tims-diann' in collection, "Should contain sample1"
            assert 'sample2-tims-diann' in collection, "Should contain sample2"

            # Test list methods
            samples = collection.list_samples()
            assert len(samples) == 2, "Should list 2 samples"

            levels = collection.list_levels(samples[0])
            assert 'precursor' in levels, "Should have precursor level"

            # Test access methods
            adata = collection[samples[0], 'precursor']
            assert adata.shape[0] > 0, "AnnData should have observations"

            print("\n✓ Basic collection test passed")
            print(f"  Loaded {len(collection)} samples")
            print(f"  Samples: {samples}")

    finally:
        import shutil
        shutil.rmtree(temp_dir)


def test_summary():
    """Test summary generation."""
    print("\n" + "=" * 80)
    print("TEST 2: SUMMARY GENERATION")
    print("=" * 80)

    zip_path, temp_dir = create_mock_zip_structure()

    try:
        with DiannCollection() as collection:
            collection.add_from_zip(zip_path, levels=['precursor'])

            # Generate summary
            summary = collection.summary_df()

            assert len(summary) == 2, "Summary should have 2 rows"
            assert 'Sample' in summary.columns, "Should have Sample column"
            assert 'precursor_shape' in summary.columns, "Should have shape columns"

            print("\n✓ Summary test passed")
            print("\nSummary DataFrame:")
            print(summary.to_string())

    finally:
        import shutil
        shutil.rmtree(temp_dir)


def test_save_load():
    """Test saving and loading collection."""
    print("\n" + "=" * 80)
    print("TEST 3: SAVE AND LOAD")
    print("=" * 80)

    zip_path, temp_dir = create_mock_zip_structure()

    try:
        # Create and save collection
        with DiannCollection() as collection:
            collection.add_from_zip(zip_path, levels=['precursor'])

            # Save
            save_path = Path(temp_dir) / "test_collection.pkl"
            collection.save(str(save_path))

            assert save_path.exists(), "Save file should exist"

        # Load collection
        loaded = DiannCollection.from_file(str(save_path))

        assert len(loaded) == 2, "Loaded collection should have 2 samples"
        assert len(loaded.list_samples()) == 2, "Should have 2 samples"

        print("\n✓ Save/load test passed")
        print(f"  Saved and loaded {len(loaded)} samples")

    finally:
        import shutil
        shutil.rmtree(temp_dir)


def test_multiple_levels():
    """Test loading multiple levels."""
    print("\n" + "=" * 80)
    print("TEST 4: MULTIPLE LEVELS")
    print("=" * 80)

    zip_path, temp_dir = create_mock_zip_structure()

    try:
        with DiannCollection() as collection:
            # Load multiple levels
            collection.add_from_zip(zip_path, levels=['precursor', 'gene'])

            # Check that both levels exist
            samples = collection.list_samples()
            assert len(samples) > 0, "Should have samples"

            levels_dict = collection.list_levels()

            # At least precursor should be loaded for all samples
            for sample in samples:
                assert 'precursor' in levels_dict[sample], f"Sample {sample} should have precursor level"

            print("\n✓ Multiple levels test passed")
            print(f"  Loaded {len(collection)} samples")
            for sample in samples:
                print(f"    {sample}: {levels_dict[sample]}")

    finally:
        import shutil
        shutil.rmtree(temp_dir)


# Run tests
if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("DIANN COLLECTION TESTS (NEW)")
    print("=" * 80 + "\n")

    try:
        test_basic_collection()
        test_summary()
        test_save_load()
        test_multiple_levels()

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
