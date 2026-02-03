#!/bin/bash

# GitHub Repository Push Script
# Run this AFTER creating the repository on GitHub

echo "=========================================="
echo "  Pushing to GitHub..."
echo "=========================================="
echo ""

cd /Users/naveensharma/.gemini/antigravity/scratch/prabhat-algo-analysis

echo "🚀 Pushing code to GitHub..."
echo ""

git push -u origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ SUCCESS! Your code is now on GitHub!"
    echo ""
    echo "🌐 View at: https://github.com/prabhat19991999sharma-ai/paper-trading-lab"
    echo ""
    echo "=========================================="
    echo "  Next: Start Backtesting"
    echo "=========================================="
    echo ""
    echo "Run these commands:"
    echo "  python3 -m venv .venv"
    echo "  source .venv/bin/activate"
    echo "  pip install -r requirements.txt"
    echo "  uvicorn app.main:app --reload"
    echo ""
    echo "Then open: http://127.0.0.1:8000"
else
    echo ""
    echo "❌ Push failed. Common reasons:"
    echo "   1. Repository not created yet on GitHub"
    echo "   2. Authentication required"
    echo ""
    echo "Make sure you've created the repository at:"
    echo "https://github.com/new"
    echo ""
    echo "Repository name: paper-trading-lab"
    echo "⚠️  DO NOT initialize with README, .gitignore, or license"
fi
