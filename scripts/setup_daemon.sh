#!/bin/bash

echo "=========================================="
echo "ConfigStream Daemon Setup"
echo "=========================================="

# Check Python version
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -e . || {
    echo "❌ Failed to install dependencies"
    exit 1
}
echo "✓ Dependencies installed"

# Create data directory
echo ""
echo "Creating data directory..."
mkdir -p data
echo "✓ Data directory: $(pwd)/data"

# Run tests
echo ""
echo "Running tests..."
pytest tests/test_scheduler.py tests/test_web_dashboard.py -v || {
    echo "⚠️  Some tests failed, but continuing..."
}

# Provide instructions
echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "To start the daemon:"
echo "  configstream daemon --interval 2 --port 8080"
echo ""
echo "Then visit:"
echo "  http://localhost:8080"
echo ""
echo "To run in background:"
echo "  nohup configstream daemon > daemon.log 2>&1 &"
echo ""
echo "To stop:"
echo "  Press Ctrl+C (or kill process if running in background)"
echo ""