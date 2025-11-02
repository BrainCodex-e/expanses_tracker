#!/bin/bash
# Start script optimized for Render free tier memory constraints
exec gunicorn --config gunicorn.conf.py app:app