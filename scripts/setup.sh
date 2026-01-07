#!/bin/bash

# Honolulu Setup Script

set -e

echo "Setting up Honolulu..."

# Check for Python 3.11+
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
    echo "Error: Python 3.11+ is required. Found: Python $PYTHON_VERSION"
    exit 1
fi

echo "Found Python $PYTHON_VERSION"

# Create virtual environment
echo "Creating Python virtual environment..."
cd packages/core
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -e ".[dev]"

# Setup CLI
echo "Setting up TypeScript CLI..."
cd ../cli
npm install
npm run build

echo ""
echo "Setup complete!"
echo ""
echo "To start the server:"
echo "  cd packages/core"
echo "  source .venv/bin/activate"
echo "  honolulu-server"
echo ""
echo "To run the CLI (in another terminal):"
echo "  cd packages/cli"
echo "  npm start"
echo ""
echo "Don't forget to set your API key:"
echo "  export ANTHROPIC_API_KEY='your-api-key'"
