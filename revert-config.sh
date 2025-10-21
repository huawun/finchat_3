#!/bin/bash

# Script to revert to original configuration

echo "🔄 Reverting to original configuration..."

if [ -f "app_original.py" ]; then
    cp app_original.py app.py
    echo "✅ Restored original app.py"
else
    echo "❌ No backup found for app.py"
fi

if [ -f "config_original.py" ]; then
    cp config_original.py config.py
    echo "✅ Restored original config.py"
else
    echo "❌ No backup found for config.py"
fi

echo "✅ Reverted to original configuration"
