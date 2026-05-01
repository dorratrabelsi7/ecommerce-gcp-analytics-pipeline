#!/bin/bash
# Test script for DirectRunner pipeline

set -e

echo "=================================================="
echo "Apache Beam DirectRunner Test"
echo "=================================================="
echo ""

# Check if Python is installed
if ! command -v python &> /dev/null; then
    echo "❌ Python not found"
    exit 1
fi

echo "✓ Python found: $(python --version)"
echo ""

# Activate virtual environment if exists
if [ -d "venv312" ]; then
    echo "Activating virtual environment..."
    source venv312/Scripts/activate 2>/dev/null || . venv312/Scripts/activate
    echo "✓ Virtual environment activated"
    echo ""
fi

# Check if data directory exists
if [ ! -d "data/raw" ]; then
    echo "❌ data/raw directory not found"
    echo "Please ensure data files are in data/raw/"
    exit 1
fi

# Check Apache Beam is installed
if ! python -c "import apache_beam" 2>/dev/null; then
    echo "❌ Apache Beam not installed"
    echo "Installing requirements..."
    pip install -r requirements.txt -q
fi

echo "📂 Data files found:"
ls -1 data/raw/ | sed 's/^/   /'
echo ""

# Create output directory
mkdir -p output
echo "✓ Output directory created: output/"
echo ""

# Run test with first file
FIRST_FILE=$(ls data/raw/*.csv 2>/dev/null | head -1)
if [ -n "$FIRST_FILE" ]; then
    echo "🚀 Running DirectRunner pipeline..."
    echo "   Input: $FIRST_FILE"
    echo "   Limit: 10 records (for quick test)"
    echo ""
    
    python beam/pipeline_directrunner.py --input "$FIRST_FILE" --limit 10
    
    echo ""
    echo "✓ Test completed successfully!"
    echo ""
    echo "📁 Output files:"
    ls -lh output/ 2>/dev/null | tail -n +2 | awk '{print "   " $9 " (" $5 ")"}'
    echo ""
    echo "💡 View results:"
    echo "   cat output/valid_*.jsonl"
    echo ""
    echo "🔄 To process all files:"
    echo "   python beam/pipeline_directrunner.py --all"
else
    echo "❌ No CSV files found in data/raw/"
    echo "Please add CSV files to data/raw/ directory"
    exit 1
fi
