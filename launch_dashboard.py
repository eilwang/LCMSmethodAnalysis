#!/usr/bin/env python3.12
"""
Quick launcher for Search Dataset Explorer Dashboard

Usage:
    ./launch_dashboard.py
    ./launch_dashboard.py --port 8080
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dashboard import launch_explorer

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='🔬 Launch Search Dataset Explorer Dashboard',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ./launch_dashboard.py                    # Default port 8050
  ./launch_dashboard.py --port 8080        # Custom port
  ./launch_dashboard.py --no-debug         # Production mode
  
After launching, open your browser to:
  http://localhost:8050 (or your custom port)
        """
    )
    
    parser.add_argument(
        '--port', 
        type=int, 
        default=8050,
        help='Port to run dashboard on (default: 8050)'
    )
    
    parser.add_argument(
        '--no-debug',
        action='store_true',
        help='Disable debug mode (for production)'
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("🔬 SEARCH DATASET EXPLORER DASHBOARD")
    print("=" * 70)
    print()
    
    try:
        launch_explorer(port=args.port, debug=not args.no_debug)
    except KeyboardInterrupt:
        print("\n\n👋 Dashboard stopped. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error starting dashboard: {e}")
        print("\nTroubleshooting:")
        print("  - Check if port is already in use")
        print("  - Try a different port: --port 8080")
        print("  - Verify dependencies: pip install dash plotly pandas")
        sys.exit(1)
