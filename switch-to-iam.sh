#!/bin/bash

# Script to switch to IAM-based configuration for EC2 deployment

echo "🔄 Switching to IAM-based configuration..."

# Backup original files
if [ ! -f "app_original.py" ]; then
    cp app.py app_original.py
    echo "✅ Backed up original app.py to app_original.py"
fi

if [ ! -f "config_original.py" ]; then
    cp config.py config_original.py
    echo "✅ Backed up original config.py to config_original.py"
fi

# Switch to improved versions
cp app_improved.py app.py
cp config_iam.py config.py

echo "✅ Switched to IAM-based configuration"
echo ""
echo "Changes made:"
echo "- app.py now uses enhanced configuration with deployment info"
echo "- config.py now prioritizes IAM roles over access keys"
echo "- Added /api/info endpoint for deployment information"
echo ""
echo "To revert: ./revert-config.sh"
