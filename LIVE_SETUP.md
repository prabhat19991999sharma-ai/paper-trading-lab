# 🔴 Live Market Setup

Yes, this system **works in the live market**, but currently in **Paper Mode** (simulated trades).

## How it Works Live
1. **Data Feed**: You need a live data source (like TrueData) to send real-time prices to the app.
2. **Strategy Engine**: The app processes these live ticks/bars instantly.
3. **Execution**: Trades are executed **virtually** (Paper Trading). It does NOT place orders on your broker account (Zerodha/Angel) yet.

---

## 🔌 Connecting Live Data (TrueData Example)

If you have a TrueData subscription, you can power this app with live NSE data immediately.

### Step 1: Install Adapter
```bash
pip install -r requirements-truedata.txt
```

### Step 2: Run the Bridge
Open a new terminal window and run:

```bash
# Replace with your TrueData credentials
export TRUEDATA_USERNAME="your_id"
export TRUEDATA_PASSWORD="your_password"

# The bridge will automatically pick up your watchlist from the app
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
