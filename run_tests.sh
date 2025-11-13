#!/bin/bash
# Test runner script for the Mergington High School Activities API

echo "🧪 Running FastAPI Tests for Mergington High School Activities API"
echo "================================================================="

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✅ Virtual environment activated"
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "🔬 Running tests with coverage..."
python -m pytest tests/ --cov=src --cov-report=html --cov-report=term-missing -v

echo ""
echo "📊 Coverage report generated in htmlcov/ directory"
echo "🎉 Test run complete!"