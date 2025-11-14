#!/bin/bash
# Cron job script to ping your Render app every 14 minutes
# Simpler alternative to the Python script

# Your app URL
APP_URL="${APP_URL:-https://expanses-tracker.onrender.com}"

# Ping the health endpoint
curl -s "${APP_URL}/status" > /dev/null 2>&1

# Log the result (optional)
if [ $? -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ Pinged $APP_URL successfully"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ❌ Failed to ping $APP_URL"
fi
