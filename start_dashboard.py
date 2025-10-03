#!/usr/bin/env python3
"""
EchoTrade Dashboard Startup Script
Quick launcher for the trading dashboard
"""

import subprocess
import sys
import webbrowser
import time
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed"""
    required_packages = ['dash', 'dash_bootstrap_components', 'plotly', 'pandas', 'numpy']
    missing = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"❌ Missing dependencies: {', '.join(missing)}")
        print("Installing missing packages...")
        subprocess.run([sys.executable, '-m', 'pip', 'install'] + missing)
    else:
        print("✅ All dependencies are installed")

def main():
    print("🚀 EchoTrade Dashboard Launcher")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path('app.py').exists():
        print("❌ app.py not found. Please run from the echotrade directory.")
        sys.exit(1)
    
    # Check dependencies
    check_dependencies()
    
    # Check if main Phase 1 components exist
    if Path('main.py').exists() and Path('config.py').exists():
        print("✅ Phase 1 backend components found")
    else:
        print("⚠️  Running in standalone mode (some features limited)")
    
    print("\n🎯 Starting Dashboard...")
    print("📊 URL: http://localhost:8050")
    print("🛑 Press Ctrl+C to stop")
    print("-" * 50)
    
    try:
        # Start the dashboard
        subprocess.run([sys.executable, 'app.py'])
    except KeyboardInterrupt:
        print("\n🛑 Dashboard stopped by user")
    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")

if __name__ == "__main__":
    main()