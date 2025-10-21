#!/bin/bash

# RedShift Chatbot Startup Script

echo "🤖 RedShift Chatbot Startup"
echo "=========================="

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "Please copy .env.example to .env and configure your credentials."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Run validation
echo "✅ Validating setup..."
python test_setup.py

if [ $? -eq 0 ]; then
    echo ""
    echo "🚀 Starting RedShift Chatbot..."
    echo "Access the application at: http://localhost:5000"
    echo "Press Ctrl+C to stop the server"
    echo ""
    python app.py
else
    echo "❌ Setup validation failed. Please check your configuration."
    exit 1
fi