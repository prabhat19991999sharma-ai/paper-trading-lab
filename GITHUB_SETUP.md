# Quick GitHub Setup - Paper Trading Lab

I cannot directly create a GitHub repository for you because it requires your GitHub account authentication. However, I've created an **interactive script** to make this super easy!

## 🚀 Automated Setup (Easiest Method)

Just run this one command:

```bash
cd /Users/naveensharma/.gemini/antigravity/scratch/prabhat-algo-analysis
./setup-github.sh
```

The script will:
1. Guide you to create the repo on GitHub
2. Ask for your GitHub username
3. Automatically push your code
4. Give you instructions to start backtesting

---

## 📝 Manual Method (If You Prefer)

### Step 1: Create Repository on GitHub

1. Go to: **https://github.com/new**
2. Fill in:
   - **Repository name**: `paper-trading-lab`
   - **Description**: `Paper trading simulator for Indian stocks`
   - **Public** or **Private** (your choice)
   - ⚠️ **DO NOT** check: README, .gitignore, or license
3. Click **"Create repository"**

### Step 2: Push Your Code

Replace `YOUR_USERNAME` with your actual GitHub username:

```bash
cd /Users/naveensharma/.gemini/antigravity/scratch/prabhat-algo-analysis

git remote add origin https://github.com/YOUR_USERNAME/paper-trading-lab.git
git push -u origin main
```

---

## ⚡ Start Backtesting After Push

```bash
# Install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run the app
uvicorn app.main:app --reload
```

Open: **http://127.0.0.1:8000**

---

## 🔐 Authentication Note

When you push, GitHub will prompt you to authenticate. You can use:
- **Personal Access Token** (recommended)
- **GitHub CLI** (if installed)
- **SSH key**

If you haven't set up authentication, GitHub will guide you through it.

---

**Ready to proceed?** Run `./setup-github.sh` and follow the prompts!
