#!/usr/bin/env python3
"""
EchoTrade Dashboard - Ultra Simple Starter
Just run: python dashboard.py
"""

print("🚀 Starting EchoTrade Pro Dashboard...")
print("📊 Open: http://localhost:8050")

try:
    from app import app
    app.run(host='0.0.0.0', port=8050, debug=False)
except Exception as e:
    print(f"❌ Error: {e}")
    print("💡 Try: pip install dash dash-bootstrap-components")