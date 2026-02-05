# 📱 Quick Deployment Guide

Your trading app is ready to deploy! Follow these simple steps:

## Step 1: Push Latest Changes to GitHub

Run these commands in your terminal:

```bash
cd ~/Desktop/DhanAlgoApp

# Add all changes
git add .

# Commit with message
git commit -m "Add backtesting framework and expand watchlist"

# Push to GitHub
git push origin main
```

## Step 2: Deploy on Render.com

1. **Go to** [render.com](https://render.com)
2. **Login/Sign up** (use your GitHub account for easy connection)
3. Click **"New +"** → **"Web Service"**
4. **Connect GitHub** and select `paper-trading-lab` repository
5. Render auto-detects `render.yaml` and Dockerfile ✅
6. Click **"Create Web Service"**

Render will build and deploy automatically (~5-10 minutes).

## Step 3: Access on Your Phone

Once deployed, Render gives you a URL like:
```
https://paper-trading-lab-xxxx.onrender.com
```

Just open this URL on your phone's browser! 📱

## ⚠️ Important Note

**Free Tier:** App "sleeps" after 15 minutes of no activity. First load after sleep takes ~30 seconds.

**To keep it always awake:** Upgrade to paid tier ($7/month) in Render settings.

## What's Deployed

✅ Live paper trading simulator  
✅ 9:30 Breakout strategy engine  
✅ Real-time WebSocket data feed  
✅ Trade history and analytics  
✅ Backtesting framework (20+ stocks)  
✅ Mobile-responsive UI

## Environment Variables (Optional)

If you want to hide your Dhan credentials from the code:

1. Remove them from `app/config.py`
2. In Render dashboard → Environment tab, add:
   - `DHAN_CLIENT_ID` = `2602058043`
   - `DHAN_ACCESS_TOKEN` = `your_token`

Then update `config.py` to read from environment:
```python
import os
dhan_client_id = os.getenv("DHAN_CLIENT_ID", "")
dhan_access_token = os.getenv("DHAN_ACCESS_TOKEN", "")
```

---

**That's it! Your app will be live in minutes.** 🚀
