#!/bin/bash

# GitHub Repository Creation Script
# This script helps create a GitHub repository for Paper Trading Lab

echo "=========================================="
echo "  Paper Trading Lab - GitHub Setup"
echo "=========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo "❌ Error: Please run this script from the project directory"
    echo "   cd /Users/naveensharma/.gemini/antigravity/scratch/prabhat-algo-analysis"
    exit 1
fi

echo "📋 Step 1: Create GitHub Repository"
echo ""
echo "Please go to: https://github.com/new"
echo ""
echo "Repository settings:"
echo "  - Name: paper-trading-lab"
echo "  - Description: Paper trading simulator for Indian stocks with 9:30 breakout strategy"
echo "  - Visibility: Public (recommended) or Private"
echo "  - ⚠️  DO NOT check: Add README, .gitignore, or license"
echo ""
echo "Press Enter after you've created the repository..."
read

echo ""
echo "📝 Step 2: Enter Your GitHub Username"
read -p "GitHub username: " github_username

if [ -z "$github_username" ]; then
    echo "❌ Username cannot be empty"
    exit 1
fi

echo ""
echo "🔗 Step 3: Connecting to GitHub..."

# Add remote
git remote add origin "https://github.com/${github_username}/paper-trading-lab.git" 2>/dev/null || {
    echo "Remote already exists, updating..."
    git remote set-url origin "https://github.com/${github_username}/paper-trading-lab.git"
}

echo ""
echo "🚀 Step 4: Pushing code to GitHub..."
echo ""

git push -u origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ SUCCESS! Your repository is now on GitHub!"
    echo ""
    echo "🌐 View it at: https://github.com/${github_username}/paper-trading-lab"
    echo ""
else
    echo ""
    echo "❌ Push failed. This might be because:"
    echo "   1. You need to authenticate with GitHub"
    echo "   2. The repository doesn't exist yet"
    echo "   3. You don't have permission"
    echo ""
    echo "Try pushing manually:"
    echo "   git push -u origin main"
fi

echo ""
echo "=========================================="
echo "  Next: Start Backtesting Locally"
echo "=========================================="
echo ""
echo "Run these commands:"
echo "  python3 -m venv .venv"
echo "  source .venv/bin/activate"
echo "  pip install -r requirements.txt"
echo "  uvicorn app.main:app --reload"
echo ""
echo "Then open: http://127.0.0.1:8000"
echo ""
