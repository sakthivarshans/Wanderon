#!/bin/bash
# WanderOn — Start backend only (for testing without the desktop UI)
echo "Starting WanderOn backend..."
cd "$(dirname "$0")/backend"
python3 main.py
