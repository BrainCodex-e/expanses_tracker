#!/usr/bin/env python3
"""
Keep-alive script to prevent Render free tier from sleeping.
Pings your app every 14 minutes to keep it active.

Usage:
    python keep_alive.py

Or run as a background service on any machine (your laptop, Raspberry Pi, etc.)
"""

import time
import requests
from datetime import datetime
import os

# Your app URL (change this to your Render URL)
APP_URL = os.environ.get("APP_URL", "https://your-app.onrender.com")

# Ping interval in seconds (10 minutes = 600 seconds)
PING_INTERVAL = 10 * 60  # 10 minutes

# Health check endpoint
HEALTH_ENDPOINT = f"{APP_URL}/status"


def ping_app():
    """Ping the app to keep it awake"""
    try:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Pinging {HEALTH_ENDPOINT}...")
        
        response = requests.get(HEALTH_ENDPOINT, timeout=30)
        
        if response.status_code == 200:
            print(f"✅ Success! Status code: {response.status_code}")
            print(f"   Response time: {response.elapsed.total_seconds():.2f}s")
        else:
            print(f"⚠️  Warning: Status code {response.status_code}")
            
    except requests.exceptions.Timeout:
        print(f"⏱️  Timeout - App might be waking up from sleep")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


def main():
    """Main loop - ping every 14 minutes"""
    print("=" * 60)
    print("🚀 Keep-Alive Service Started")
    print("=" * 60)
    print(f"App URL: {APP_URL}")
    print(f"Ping Interval: {PING_INTERVAL // 60} minutes")
    print(f"Health Endpoint: {HEALTH_ENDPOINT}")
    print("=" * 60)
    print()
    print("Press Ctrl+C to stop")
    print()
    
    # Initial ping
    ping_app()
    
    # Keep pinging
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
