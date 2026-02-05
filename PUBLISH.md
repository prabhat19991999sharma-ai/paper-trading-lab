# How to Publish Your App

## 1. Move Project to Desktop
Run this command in your terminal to move the project to your Desktop:
```bash
mv /Users/naveensharma/.gemini/antigravity/scratch/prabhat-algo-analysis ~/Desktop/DhanAlgoApp
```

## 2. Push to GitHub
1.  Create a **New Repository** on GitHub (e.g., `dhan-algo-app`).
2.  Open terminal in your project folder:
    ```bash
    cd ~/Desktop/DhanAlgoApp
    git init
    git add .
    git commit -m "Initial commit with Dhan Integration and New UI"
    git branch -M main
    git remote add origin https://github.com/YOUR_USERNAME/dhan-algo-app.git
    git push -u origin main
    ```

## 3. Deploy on Render
1.  Sign up/Login to [Render.com](https://render.com).
2.  Click **New +** -> **Web Service**.
3.  Connect your GitHub repository.
4.  Render will auto-detect the `render.yaml` file and configure everything.
5.  **Environment Variables**:
    - In the Render Dashboard, go to **Environment** tab.
    - Add these secrets if you didn't commit them in `config.py` (Recommended):
        - `DHAN_CLIENT_ID`: Your ID
        - `DHAN_ACCESS_TOKEN`: Your Token

## 4. Done!
Your app will be live at `https://dhan-algo-app.onrender.com`.
