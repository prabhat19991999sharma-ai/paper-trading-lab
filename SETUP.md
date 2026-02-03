# Setup Instructions

## 🚀 Quick Start - GitHub Repository

### Step 1: Create GitHub Repository

1. Go to [GitHub](https://github.com/new)
2. Create a new repository:
   - **Name**: `paper-trading-lab` (or any name you prefer)
   - **Description**: "Paper trading simulator for Indian stocks with 9:30 breakout strategy"
   - **Visibility**: Public or Private (your choice)
   - ⚠️ **DO NOT** initialize with README, .gitignore, or license (we already have these)
3. Click **Create repository**

### Step 2: Connect & Push to GitHub

After creating the repository, GitHub will show you commands. Run these in your terminal:

```bash
cd /Users/naveensharma/.gemini/antigravity/scratch/prabhat-algo-analysis

# Add your GitHub repository (replace with YOUR username and repo name)
git remote add origin https://github.com/YOUR_USERNAME/paper-trading-lab.git

# Push your code
git push -u origin main
```

**Replace `YOUR_USERNAME` with your actual GitHub username!**

---

## 💻 Running Locally for Backtesting

### Step 1: Install Python Dependencies

```bash
cd /Users/naveensharma/.gemini/antigravity/scratch/prabhat-algo-analysis

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Start the Application

```bash
# Make sure you're in the project directory with venv activated
uvicorn app.main:app --reload
```

### Step 3: Open Dashboard

Open your browser and go to:
```
http://127.0.0.1:8000
```

### Step 4: Run Your First Backtest

1. The app auto-loads sample data on first run
2. Click **"Run Simulation"** button
3. View results in the dashboard:
   - Daily P&L
   - Win rate
   - Trade log
   - Equity curve

---

## 📊 Upload Your Own Data

### CSV Format Required

Your CSV file must have these columns:
```
ts,symbol,open,high,low,close,volume
2026-02-03 09:15,RELIANCE,2750.00,2752.10,2749.30,2751.25,12000
2026-02-03 09:16,RELIANCE,2751.25,2753.50,2751.00,2752.80,15000
```

### Upload Steps

1. Click **"Choose File"** under "Upload CSV (1-minute bars)"
2. Select your CSV file
3. Click **"Upload Data"**
4. Click **"Run Simulation"**
5. Review results

---

## 🔧 Troubleshooting

### Port Already in Use
If you see "Address already in use" error:
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Or use a different port
uvicorn app.main:app --reload --port 8001
```

### Module Not Found
Make sure virtual environment is activated:
```bash
source .venv/bin/activate
```

### Database Locked
Stop the server and restart it:
```bash
# Press Ctrl+C to stop
# Then run again
uvicorn app.main:app --reload
```

---

## 📁 Project Location

Your project is located at:
```
/Users/naveensharma/.gemini/antigravity/scratch/prabhat-algo-analysis
```

**Recommendation**: Consider moving this to a more permanent location like:
```bash
# Example: move to Documents
mv /Users/naveensharma/.gemini/antigravity/scratch/prabhat-algo-analysis ~/Documents/paper-trading-lab

# Then work from there
cd ~/Documents/paper-trading-lab
```
