#!/bin/bash

echo "🏠 Spitogatos Apartment Monitor - Quick Setup"
echo "=============================================="
echo ""

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed!"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1-2)
echo "✅ Python $PYTHON_VERSION found"
echo ""

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Copy .env.example to .env
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file and add your credentials!"
else
    echo "✅ .env file already exists"
fi

# Make script executable
chmod +x spitogatos_monitor.py

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your credentials (Telegram or Email)"
echo "2. Test: python spitogatos_monitor.py"
echo "3. Setup cron job (see README.md)"
echo ""
echo "For GitHub Actions setup, see README.md"
echo ""
