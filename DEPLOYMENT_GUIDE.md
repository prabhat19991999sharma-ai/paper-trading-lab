# ☁️ How to Publish Your Website (Render.com)

Since GitHub Pages cannot run Python/DB apps, we use **Render.com** (it has a great free tier).

## Step 1: Create Render Account
1. Go to [dashboard.render.com](https://dashboard.render.com/)
2. Sign up / Log in with **GitHub** (easiest way)

## Step 2: Create Web Service
1. Click **"New +"** button (top right)
2. Select **"Web Service"**
3. Under "Connect a repository", click **"Connect"** next to `paper-trading-lab`
   - *If you don't see it, click "Configure account" to grant Render access to your new repo*

## Step 3: Configure & Deploy
Render will auto-detect the configuration I pushed (`render.yaml`).

1. **Name**: `paper-trading-lab` (or any name)
2. **Region**: Singapore (closest to India) or Frankfurt
3. **Branch**: `main`
4. **Instance Type**: Select **"Free"**
5. Click **"Create Web Service"**

## 🚀 That's it!
Render will now build your app. It takes about **2-3 minutes**.
Once done, you'll see a URL like:
`https://paper-trading-lab.onrender.com`

**Click that URL to see your live website!** 🌍
