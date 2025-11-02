#!/usr/bin/env bash
# Simple helper to run the expense tracker locally with example credentials

export USERS="Erez26:expansesforever21,bob:password456"
export SECRET_KEY="dev-secret-key-change-for-production"
export PORT=8000

echo "Starting expense tracker with example users:"
echo "  - Erez26 / expansesforever21"
echo "  - bob / password456"
echo ""
echo "Open: http://127.0.0.1:8000"
echo "From phone (same WiFi): http://$(hostname -I | awk '{print $1}'):8000"
echo ""

python3 app.py