#!/bin/bash
set -euo pipefail

echo "=========================================="
echo "ConfigStream Daemon Setup"
echo "=========================================="

# Verify python and pip availability
if ! command -v python >/dev/null 2>&1; then
  echo "❌ 'python' not found in PATH"
  exit 1
fi
if ! command -v pip >/dev/null 2>&1; then
  echo "❌ 'pip' not found in PATH"
  exit 1
fi

# Check Python version (require >= 3.8)
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"
py_major=$(echo "$python_version" | cut -d. -f1)
py_minor=$(echo "$python_version" | cut -d. -f2)
if [ "$py_major" -lt 3 ] || { [ "$py_major" -eq 3 ] && [ "$py_minor" -lt 8 ]; }; then
  echo "❌ Python >= 3.8 is required (found $python_version)"
  exit 1
fi

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
if ! command -v pytest >/dev/null 2>&1; then
    printf '%s\n' "❌ 'pytest' not found; please install dev dependencies (e.g., pip install -e .[dev])"
    exit 1
fi
pytest tests/test_scheduler.py tests/test_web_dashboard.py -v || {
    printf '%s\n' "⚠️ Some tests failed, but continuing..."
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