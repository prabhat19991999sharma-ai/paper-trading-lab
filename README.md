# Paper Trading Lab

A beginner‑friendly paper‑trading simulator for Indian stocks using 1‑minute bars. It runs locally, stores data in SQLite, and shows daily results in a web dashboard.

## Quick Start

1. Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run the app

```bash
uvicorn app.main:app --reload
```

3. Open the dashboard

```
http://127.0.0.1:8000
```

The app auto-loads `data/sample_bars.csv` the first time it starts. Use the **Reset Data** button to return to the sample dataset after testing your own uploads.

## Live Replay Mode

The **Live Replay** panel streams your CSV bars in real time to the simulator and updates the dashboard live using WebSockets.

- Choose a speed (1x = 1 minute per bar, 60x = 1 second per bar).
- Click **Start Live** to replay bars.
- Click **Stop** to pause the stream.

This is a safe, free way to test live behavior without using licensed NSE data.

## TrueData Live Adapter (licensed feed)

TrueData provides licensed NSE market data. If your plan and agreements allow redistribution or use in virtual trading, you can connect it to this app.

### Install adapter dependencies

```bash
pip install -r requirements-truedata.txt
```

### Run the bridge

```bash
export TRUEDATA_USERNAME="your_id"
export TRUEDATA_PASSWORD="your_password"
export TRUEDATA_SYMBOLS="RELIANCE,TCS,INFY"
# ticks | one_min | both
export TRUEDATA_MODE="ticks"

python3 scripts/truedata_bridge.py
```

The bridge will POST ticks/bars into:
- `POST /api/ingest/tick`
- `POST /api/ingest/bar`

If your TrueData subscription enables 1‑minute bars, you can set `TRUEDATA_MODE=one_min`.

### Watchlist from the UI

If you leave `TRUEDATA_SYMBOLS` empty, the bridge will pull the watchlist from:

```
GET /api/watchlist
```

Use the **Symbol Watchlist** section in the UI to edit symbols. The bridge polls this list every 30 seconds by default.

### Auto‑reconnect + backfill

The bridge auto‑reconnects if the stream goes stale and attempts to backfill recent 1‑minute bars (when the TrueData history API is available).

Environment knobs:

```
TRUEDATA_WATCHLIST_POLL=30        # seconds
TRUEDATA_STALE_AFTER=30           # seconds without ticks/bars to trigger reconnect
TRUEDATA_BACKFILL_MINUTES=5       # backfill window
TRUEDATA_RECONNECT_BACKOFF=5      # seconds between reconnect attempts
```

## Live Ingestion API (for any feed)

When you plug in a licensed data source, push ticks or bars into the app using these endpoints:

### Tick ingestion
```
POST /api/ingest/tick
{
  "ts": "2026-02-03 09:31:04",
  "symbol": "RELIANCE",
  "price": 2752.15,
  "volume": 250
}
```

Ticks are aggregated into 1‑minute bars automatically. When a bar closes, it is stored and fed into the strategy engine.

### Bar ingestion
```
POST /api/ingest/bar
{
  "ts": "2026-02-03 09:31",
  "symbol": "RELIANCE",
  "open": 2751.2,
  "high": 2753.1,
  "low": 2750.8,
  "close": 2752.7,
  "volume": 12000
}
```

### Flush remaining bars
```
POST /api/ingest/flush
```

## Strategy Risk Limits

Config lives in `app/config.py`:

- `max_risk_pct`: risk per trade as % of equity
- `max_trades_per_day_global`: total daily trades cap
- `max_trades_per_day_per_symbol`: per‑symbol daily trades cap
- `max_daily_loss`: stop trading after daily loss threshold

## CSV Format

Upload 1‑minute bars with the following headers:

```
ts,symbol,open,high,low,close,volume
2026-02-02 09:15,RELIANCE,2750.00,2752.10,2749.30,2751.25,12000
```

Notes:
- `ts` should be local market time (IST). If no timezone is included, the app assumes Asia/Kolkata.
- The simulator uses your strategy: breakout of 09:30 high and first 30 minutes high, 2R target, one trade per day.

## Data Rights Note

Real‑time market data for NSE stocks is a licensed product. This project is designed to work with delayed data, CSV uploads, or licensed feeds you already have.
