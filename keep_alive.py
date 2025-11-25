#!/usr/bin/env python3
"""
Keep-alive script to prevent Render free tier from sleeping.
Uses curl to download the page every 10 minutes to keep it active.

Usage:
    python keep_alive.py

Or run as a background service on any machine (your laptop, Raspberry Pi, etc.)
"""

import time
from datetime import datetime
import os
import subprocess

# Your app URL (change this to your Render URL)
APP_URL = os.environ.get("APP_URL", "https://expanses-tracker.onrender.com")

# Ping interval in seconds (5 minutes = 300 seconds)
PING_INTERVAL = 5 * 60  # 5 minutes

# Health check endpoint
HEALTH_ENDPOINT = f"{APP_URL}/status"


def ping_app():
    """Ping the app to keep it awake using curl to download the page and power up the server"""
    try:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Curling {HEALTH_ENDPOINT} to keep server awake...")
        
        result = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", "30", HEALTH_ENDPOINT], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            status_code = result.stdout.strip()
            print(f"✅ Success! Status code: {status_code}")
        else:
            print(f"⚠️  Warning: Curl failed with return code {result.returncode}")
            if result.stderr:
                print(f"   Error: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """Main loop - curl every 10 minutes"""
    print("=" * 60)
    print("🚀 Keep-Alive Service Started (using curl)")
    print("=" * 60)
    print(f"App URL: {APP_URL}")
    print(f"Curl Interval: {PING_INTERVAL // 60} minutes")
    print(f"Health Endpoint: {HEALTH_ENDPOINT}")
    print("=" * 60)
    print()
    print("Press Ctrl+C to stop")
    print()
    
    # Initial curl
    ping_app()
    
    # Keep curling
    try:
        while True:
            time.sleep(PING_INTERVAL)
            ping_app()
            
    except KeyboardInterrupt:
        print()
        print("=" * 60)
        print("🛑 Keep-Alive Service Stopped")
        print("=" * 60)


if __name__ == "__main__":
    main()
