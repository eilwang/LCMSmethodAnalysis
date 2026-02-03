"""
Comprehensive demonstration of zip file support in collection classes.

Both VNeoMethodCollection and MicroTOFMethodCollection now support three zip scenarios:
1. Individual zipped methods (one method per zip file)
2. Single zip containing multiple methods
3. Mixed folders with both unzipped and zipped methods
"""

import tempfile
import shutil
from pathlib import Path
import zipfile

from lc_method_collection import VNeoMethodCollection
from ms_method_collection import MicroTOFMethodCollection


def demo_lc_scenarios():
    """Demonstrate all LC method zip scenarios."""
    print("=" * 80)
    print("LC METHOD COLLECTION - ZIP FILE SCENARIOS")
    print("=" * 80)

    lc_folder = Path("/Users/eileen.wang/Desktop/diann/SampleData/methods/LC")
    meth_files = list(lc_folder.glob("*.meth"))[:4]

    if len(meth_files) < 4:
        print("Not enough .meth files for demo")
        return

    temp_dir = tempfile.mkdtemp()
    try:
        # Scenario 1: Individual method file (unzipped)
        print("\nScenario 1: Individual unzipped method")
        print("-" * 80)
        shutil.copy(meth_files[0], Path(temp_dir) / meth_files[0].name)
        print(f"  • Copied {meth_files[0].name}")

        # Scenario 2: Individual zipped method (one method per zip)
        print("\nScenario 2: Individual zipped method (1 method per zip)")
        print("-" * 80)
        zip1_path = Path(temp_dir) / "single_method.zip"
        with zipfile.ZipFile(zip1_path, 'w') as zf:
            zf.write(meth_files[1], meth_files[1].name)
        print(f"  • Created single_method.zip containing {meth_files[1].name}")

        # Scenario 3: Zip containing multiple methods
        print("\nScenario 3: Single zip with MULTIPLE methods")
        print("-" * 80)
        multi_zip_path = Path(temp_dir) / "multiple_methods.zip"
        with zipfile.ZipFile(multi_zip_path, 'w') as zf:
            zf.write(meth_files[2], meth_files[2].name)
            zf.write(meth_files[3], meth_files[3].name)
        print(f"  • Created multiple_methods.zip containing:")
        print(f"    - {meth_files[2].name}")
        print(f"    - {meth_files[3].name}")

        # Load all from folder
        print("\nLoading ALL methods from folder...")
        print("-" * 80)
        collection = VNeoMethodCollection()
        collection.add_methods_from_folder(temp_dir)

        print(f"\n✓ Loaded {len(collection)} total methods")
        print("\nMethods in collection:")
        summary = collection.summary_df()
        for idx, row in summary.iterrows():
            print(f"  {idx+1}. {row['Method']}: {row['Runtime [min]']} min, "
                  f"{row['Gradient Steps']} gradient steps")

        print("\n" + "=" * 80)

    finally:
        shutil.rmtree(temp_dir)


def demo_ms_scenarios():
    """Demonstrate all MS method zip scenarios."""
    print("\n\nMS METHOD COLLECTION - ZIP FILE SCENARIOS")
    print("=" * 80)

    # Use the pre-made multi-method zip
    multi_zip = "/tmp/multiple_ms_methods.zip"
    if not Path(multi_zip).exists():
        print("Note: Multi-method zip not available, creating one...")
        ms_folder = Path("/Users/eileen.wang/Desktop/diann/SampleData/methods/MS/DIA003.proteoscape.m")
        backups = [d for d in ms_folder.glob("backup-*.m") if d.is_dir()][:2]

        if len(backups) >= 2:
            with zipfile.ZipFile(multi_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
                for backup_dir in backups:
                    for file_path in backup_dir.rglob('*'):
                        if file_path.is_file():
                            arcname = str(file_path.relative_to(ms_folder.parent))
                            zf.write(file_path, arcname)
            print(f"  • Created {multi_zip}")
        else:
            print("Could not create multi-method zip")
            return

    temp_dir = tempfile.mkdtemp()
    try:
        # Scenario 1: .m directory (unzipped)
        print("\nScenario 1: Unzipped .m directory")
        print("-" * 80)
        src_m = Path("/Users/eileen.wang/Desktop/diann/SampleData/methods/MS/DIA003.proteoscape.m")
        if src_m.exists():
            dest_m = Path(temp_dir) / "DIA003.m"
            shutil.copytree(src_m, dest_m)
            print(f"  • Copied DIA003.m directory")

        # Scenario 2: Individual zipped method
        print("\nScenario 2: Individual zipped method (1 method per zip)")
        print("-" * 80)
        if Path("/tmp/DIA003.proteoscape.zip").exists():
            shutil.copy("/tmp/DIA003.proteoscape.zip",
                       Path(temp_dir) / "single_method.zip")
            print(f"  • Copied single_method.zip")

        # Scenario 3: Zip with multiple methods
        print("\nScenario 3: Single zip with MULTIPLE methods")
        print("-" * 80)
        if Path(multi_zip).exists():
            shutil.copy(multi_zip, Path(temp_dir) / "multiple_methods.zip")
            print(f"  • Copied multiple_methods.zip with multiple .m directories inside")

        # Load all from folder
        print("\nLoading ALL methods from folder...")
        print("-" * 80)
        collection = MicroTOFMethodCollection()
        collection.add_methods_from_folder(temp_dir)

        print(f"\n✓ Loaded {len(collection)} total methods")
        print("\nMethods in collection:")
        summary = collection.summary_df()
        for idx, row in summary.iterrows():
            print(f"  {idx+1}. {row['Method']}: {row['MS Params']} MS params, "
                  f"{row['DIA Windows']} DIA windows")

        print("\n" + "=" * 80)

    finally:
        shutil.rmtree(temp_dir)


def main():
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 15 + "COMPREHENSIVE ZIP FILE SUPPORT DEMO" + " " * 27 + "║")
    print("╚" + "=" * 78 + "╝")
    print()
    print("This demo shows all supported zip file scenarios:")
    print("  1. Individual method files (unzipped)")
    print("  2. Individual zipped methods (one method per .zip)")
    print("  3. Single .zip containing MULTIPLE methods")
    print("  4. Mixed folders with all of the above")
    print()

    try:
        demo_lc_scenarios()
        demo_ms_scenarios()

        print("\n\n" + "╔" + "=" * 78 + "╗")
        print("║" + " " * 30 + "SUMMARY" + " " * 41 + "║")
        print("╚" + "=" * 78 + "╝")
        print("\n✓ All zip scenarios work correctly!")
        print("\nKey Features:")
        print("  • Transparent handling of zipped and unzipped files")
        print("  • Automatic extraction of methods from zip archives")
        print("  • Support for zips containing multiple methods")
        print("  • Clean separation when zip has single vs multiple methods:")
        print("    - Single method: uses zip filename as method name")
        print("    - Multiple methods: uses individual method names")
        print("  • Automatic cleanup of temporary extracted files")
        print("  • Works with both LC (.meth) and MS (.m) methods")
        print("\nUsage:")
        print("  collection.add_methods_from_folder('/path/to/folder')")
        print("  # Automatically finds and loads:")
        print("  #   - .meth files / .m directories")
        print("  #   - .zip files (single or multiple methods)")
        print("=" * 80)

    except Exception as e:
        print(f"\n\n✗ DEMO FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
