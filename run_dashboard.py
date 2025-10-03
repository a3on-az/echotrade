#!/usr/bin/env python3
"""
Simple EchoTrade Dashboard Launcher
"""

import sys
import webbrowser
import time
from threading import Timer

def open_browser():
    """Open browser after server starts"""
    time.sleep(2)  # Wait for server to start
    webbrowser.open('http://localhost:8050')

if __name__ == "__main__":
    print("🚀 EchoTrade Pro Dashboard")
    print("=" * 40)
    print("📊 URL: http://localhost:8050")
    print("🛑 Press Ctrl+C to stop")
    print("-" * 40)
    
    # Auto-open browser in 2 seconds
    Timer(2.0, open_browser).start()
    
    try:
        # Import and run the app
        from app import app
        app.run(
            debug=False,  # Disable debug for cleaner output
            host='0.0.0.0',
            port=8050
        )
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped!")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)