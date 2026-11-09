#!/bin/bash
cd "$(dirname "$0")"
echo "Starting Trading Terminal on http://0.0.0.0:8080"
echo "Open on your tablet: http://<your-ip>:8080"
python server.py
