#!/bin/bash

echo "🔍 Verifying Static Conversion..."
echo ""

# Check if Flask files are removed
echo "Checking for removed Flask files..."
FLASK_FILES=(
    "src/configstream/web_dashboard.py"
    "src/configstream/api.py"
    "src/configstream/main_daemon.py"
    "src/configstream/scheduler.py"
)

for file in "${FLASK_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "❌ $file still exists (should be deleted)"
    else
        echo "✅ $file removed"
    fi
done

echo ""
echo "Checking for required files..."
REQUIRED_FILES=(
    ".github/workflows/merge.yml"
    "index.html"
    "sources.txt"
    "README.md"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file exists"
    else
        echo "❌ $file missing"
    fi
done

echo ""
echo "Checking output directory..."
if [ -d "output" ]; then
    echo "✅ output/ directory exists"
    ls -lh output/
else
    echo "⚠️  output/ directory will be created by GitHub Actions"
fi

echo ""
echo "✨ Verification complete!"