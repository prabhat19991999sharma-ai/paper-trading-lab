# Backtesting Guide

## Overview

This guide explains how to backtest your 9:30 Breakout + First 30 Min High strategy using historical data from the Dhan API.

## Prerequisites

### 1. Dhan API Credentials

You need:
- **Client ID**: Your Dhan client ID (e.g., `260205804`)
- **Access Token**: A JWT token from Dhan API

Your credentials are already configured in `app/config.py`:
- `dhan_client_id = "260205804"`
- `dhan_access_token = "eyJhbGc..."`

> [!IMPORTANT]
> Your access token expires on **2026-02-12** (based on the JWT expiry). You'll need to generate a new token after that date.

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `pandas` - Data manipulation
- `numpy` - Numerical calculations
- `requests` - API calls

## Running a Backtest

### Command-Line Interface (CLI)

The easiest way to run a backtest is using the CLI:

```bash
python app/backtest_runner.py \
  --symbols RELIANCE TCS INFY \
  --start-date 2024-01-01 \
  --end-date 2024-12-31
```

### CLI Arguments

**Required:**
- `--symbols` - Stock symbols to test (space-separated)
- `--start-date` - Start date (YYYY-MM-DD format)
- `--end-date` - End date (YYYY-MM-DD format)

**Optional:**
- `--capital` - Initial capital (default: ₹100,000)
- `--risk-pct` - Risk per trade as % of equity (default: 0.01 = 1%)
- `--risk-reward` - Risk/reward ratio (default: 2.0)
- `--output` - Save trade results to CSV file
- `--no-cache` - Force fresh API fetch (ignore cache)
- `--verbose` - Enable debug logging

### Example: Full Backtest with Output

```bash
python app/backtest_runner.py \
  --symbols RELIANCE TCS INFY HDFCBANK \
  --start-date 2024-01-01 \
  --end-date 2024-12-31 \
  --capital 500000 \
  --risk-pct 0.02 \
  --output backtest_results.csv
```

## Performance Metrics Explained

After running a backtest, you'll see:

### 📊 Trade Statistics
- **Total Trades**: Number of trades executed
- **Wins/Losses**: Winning vs losing trades
- **Win Rate**: Percentage of winning trades

### 💰 Returns
- **Initial Capital**: Starting amount
- **Final Equity**: Ending amount
- **Total Return**: Profit/loss in ₹
- **Return %**: Percentage gain/loss
- **Annualized %**: Return extrapolated to 1 year

### 📈 Win/Loss Analysis
- **Avg Win**: Average profit per winning trade
- **Avg Loss**: Average loss per losing trade
- **Max Win**: Largest single win
- **Max Loss**: Largest single loss
- **Profit Factor**: Total wins ÷ Total losses (> 1 is good)

### ⚠️ Risk Metrics
- **Avg R-Multiple**: Average return in terms of risk units
  - 2R means you made 2x your risk on average
  - -1R means you lost your risk amount
- **Max Drawdown**: Largest peak-to-trough decline
- **Sharpe Ratio**: Risk-adjusted return (higher is better)
- **Sortino Ratio**: Like Sharpe but only considers downside risk

## Data Caching

Historical data is cached locally to avoid repeated API calls:

**Cache Location**: `data/backtest_cache/`

**Cache Files**: Named as `{SYMBOL}_{INTERVAL}_{START}_{END}.csv`

Example: `RELIANCE_1min_2024-01-01_2024-12-31.csv`

### Managing Cache

**View cache:**
```bash
ls -lh data/backtest_cache/
```

**Clear cache:**
```bash
rm -rf data/backtest_cache/*
```

**Force fresh data:**
```bash
python app/backtest_runner.py --symbols RELIANCE --start-date 2024-01-01 --end-date 2024-12-31 --no-cache
```

## API Rate Limits

The Dhan API has limitations:

1. **Intraday Data**: Maximum 90 days per request
   - The backtester automatically splits requests into 90-day chunks
   
2. **Rate Limiting**: 0.5 second delay between requests (configurable)

3. **Data Availability**:
   - Intraday (1-min): Last 5 years
   - Daily: From stock inception

## Supported Symbols

Currently mapped symbols (in `app/dhan_client.py`):

- RELIANCE
- TCS
- INFY
- HDFCBANK
- ICICIBANK
- HINDUNILVR
- SBIN
- BHARTIARTL
- ITC
- KOTAKBANK

> [!NOTE]
> To add more symbols, you need their Dhan Security IDs. Download the [Dhan Scrip Master CSV](https://api.dhan.co/securitylist) and update the mapping in `dhan_client.py`.

## Programmatic Usage

You can also run backtests from Python code:

```python
from app.dhan_client import DhanHistoricalClient
from app.backtester import Backtester
from app.performance import PerformanceAnalyzer
from app.config import CONFIG

# Fetch data
client = DhanHistoricalClient(
    client_id=CONFIG.dhan_client_id,
    access_token=CONFIG.dhan_access_token
)

bars_df = client.fetch_historical_intraday(
    symbol="RELIANCE",
    start_date="2024-01-01",
    end_date="2024-12-31",
    interval="1"
)

# Run backtest
backtester = Backtester(initial_capital=100000)
results = backtester.run(bars_df)

# Calculate metrics
metrics = PerformanceAnalyzer.calculate_metrics(results)
PerformanceAnalyzer.print_summary(metrics)
```

## Troubleshooting

### "Security ID not found for SYMBOL"

The symbol isn't in the mapping. Add it to `security_map` in `app/dhan_client.py`:

```python
self.security_map = {
    "YOURSYMBOL": "SECURITY_ID_HERE",
    ...
}
```

### "API request failed: 401 Unauthorized"

Your access token has expired. Generate a new one from Dhan and update `app/config.py`.

### "No data fetched for SYMBOL"

- Check if the symbol is listed on NSE
- Verify the date range (must be within last 5 years for intraday)
- Try with `--no-cache` to force fresh fetch

### Slow backtest performance

- Use cached data (don't use `--no-cache` repeatedly)
- Reduce date range or number of symbols
- The first run will be slow as it fetches data; subsequent runs use cache

## Best Practices

1. **Start Small**: Test with 1-2 symbols and 3-6 months first
2. **Use Cache**: Let the system cache data for faster subsequent runs
3. **Review Trades**: Use `--output` to export trades and analyze them
4. **Parameter Optimization**: Try different `--risk-pct` and `--capital` values
5. **Validate Results**: Compare metrics across different time periods

## Next Steps

After backtesting:

1. **Analyze the results** - Is the win rate acceptable? Is max drawdown manageable?
2. **Test different periods** - Does the strategy work across bull/bear markets?
3. **Optimize parameters** - Experiment with risk limits and position sizing
4. **Paper trade first** - Use the existing paper trading simulator before going live
5. **Go live carefully** - Start with small capital once confident

## Security Note

> [!CAUTION]
> Your Dhan access token is stored in `config.py`. Make sure this file is in `.gitignore` to prevent accidentally committing your credentials to version control.

Check your `.gitignore`:
```bash
cat .gitignore
```

Should contain:
```
__pycache__/
*.pyc
.venv/
papertrade.db
app/config.py  # Add this if not present
```
