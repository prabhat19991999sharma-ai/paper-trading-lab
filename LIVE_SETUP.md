# 🔴 Live Market Setup

Yes, this system **works in the live market**, but currently in **Paper Mode** (simulated trades).

## How it Works Live
1. **Data Feed**: You need a live data source (like TrueData) to send real-time prices to the app.
2. **Strategy Engine**: The app processes these live ticks/bars instantly.
3. **Execution**: Trades are executed **virtually** (Paper Trading). It does NOT place orders on your broker account (Zerodha/Angel) yet.

---

## 🔌 Connecting Live Data

### Option A: Angel One (Free for Users)
If you have an Angel One account, use our bridge to stream data for free.

1. **Install Dependencies**:
   ```bash
   pip install -r requirements-angel.txt
   ```

2. **Run the Bridge**:
   (In a separate terminal window)
   ```bash
   export ANGEL_API_KEY="..."
   export ANGEL_CLIENT_ID="..."
   export ANGEL_PASSWORD="..."
   export ANGEL_TOTP_KEY="..."

   python3 scripts/angel_bridge.py
   ```
   *Note: This script has a predefined list of tokens (RELIANCE, INFY, etc.). Edit `scripts/angel_bridge.py` to maps newer stocks.*

### Option B: TrueData (Paid Feed)
If you have a TrueData subscription:
```bash
export TRUEDATA_USERNAME="..."
export TRUEDATA_PASSWORD="..."
python3 scripts/truedata_bridge.py
```

### Step 3: Watch it Run
- The bridge feeds live prices to the dashboard.
- The strategy runs in real-time.
- Trades appear in the "Trades" table as they happen.

---

## ❓ Can it place REAL orders?
Not out of the box. Currently, it is a **Paper Trading Lab**.

To place real orders, we would need to add an integration with a broker API (like Angel One SmartAPI, Zerodha Kite, or Dhan).

**Would you like me to add a broker integration?**
