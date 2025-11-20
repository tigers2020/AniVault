#!/bin/bash
# AniVault GUI 실행 스크립트

echo "Starting AniVault GUI..."
python3 run_gui.py

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ AniVault GUI failed to start"
    echo "💡 Make sure Python is installed and accessible"
    exit 1
fi
