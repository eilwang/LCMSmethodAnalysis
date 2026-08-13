#!/usr/bin/env python3
"""
Test Dashboard Setup

Quick test to verify the dashboard is properly installed and can be imported.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test if all required modules can be imported."""
    print("Testing imports...")
    
    errors = []
    
    # Test dashboard module
    try:
        from dashboard import launch_explorer, SearchExplorerDashboard
        print("  ✅ Dashboard module")
    except ImportError as e:
        print(f"  ❌ Dashboard module: {e}")
        errors.append(("Dashboard", str(e)))
    
    # Test dash
    try:
        import dash
        print("  ✅ Dash")
    except ImportError as e:
        print(f"  ❌ Dash: {e}")
        errors.append(("Dash", str(e)))
        
    # Test plotly
    try:
        import plotly
        print("  ✅ Plotly")
    except ImportError as e:
        print(f"  ❌ Plotly: {e}")
        errors.append(("Plotly", str(e)))
    
    # Test parsers
    try:
        from parsers.search import SearchCollection, SearchLoader
        print("  ✅ Search parsers")
    except ImportError as e:
        print(f"  ❌ Search parsers: {e}")
        errors.append(("Search parsers", str(e)))
    
    # Test pandas
    try:
        import pandas
        print("  ✅ Pandas")
    except ImportError as e:
        print(f"  ❌ Pandas: {e}")
        errors.append(("Pandas", str(e)))
    
    # Test numpy
    try:
        import numpy
        print("  ✅ NumPy")
    except ImportError as e:
        print(f"  ❌ NumPy: {e}")
        errors.append(("NumPy", str(e)))
    
    return errors


def test_file_structure():
    """Test if all expected files exist."""
    print("\nTesting file structure...")
    
    expected_files = [
        "dashboard/__init__.py",
        "dashboard/search_explorer.py",
        "dashboard/README.md",
        "dashboard/QUICK_REFERENCE.md",
        "launch_dashboard.py",
        "DASHBOARD_SETUP.md",
        "requirements.txt",
    ]
    
    missing = []
    for file_path in expected_files:
        full_path = project_root / file_path
        if full_path.exists():
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path} (missing)")
            missing.append(file_path)
    
    return missing


def test_launcher_executable():
    """Test if launcher is executable."""
    print("\nTesting launcher permissions...")
    
    launcher = project_root / "launch_dashboard.py"
    if launcher.exists():
        import os
        import stat
        
        st = os.stat(launcher)
        is_executable = bool(st.st_mode & stat.S_IXUSR)
        
        if is_executable:
            print("  ✅ Launcher is executable")
            return True
        else:
            print("  ⚠️  Launcher exists but is not executable")
            print("      Run: chmod +x launch_dashboard.py")
            return False
    else:
        print("  ❌ Launcher not found")
        return False


def main():
    """Run all tests."""
    print("=" * 70)
    print("🔬 DASHBOARD SETUP TEST")
    print("=" * 70)
    print()
    
    # Test imports
    import_errors = test_imports()
    
    # Test file structure
    missing_files = test_file_structure()
    
    # Test launcher
    launcher_ok = test_launcher_executable()
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    all_ok = not import_errors and not missing_files and launcher_ok
    
    if all_ok:
        print("\n✅ All tests passed!")
        print("\n🚀 Dashboard is ready to use!")
        print("\nTo start the dashboard:")
        print("  ./launch_dashboard.py")
        print("\nOr:")
        print("  python dashboard/search_explorer.py")
        return 0
    else:
        print("\n❌ Some tests failed!")
        
        if import_errors:
            print("\n📦 Missing dependencies:")
            for name, error in import_errors:
                print(f"  - {name}: {error}")
            print("\nInstall with:")
            print("  pip install -r requirements.txt")
        
        if missing_files:
            print("\n📁 Missing files:")
            for file in missing_files:
                print(f"  - {file}")
        
        if not launcher_ok:
            print("\n⚠️  Launcher needs execute permission:")
            print("  chmod +x launch_dashboard.py")
        
        return 1


if __name__ == "__main__":
    sys.exit(main())
