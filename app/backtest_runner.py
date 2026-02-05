#!/usr/bin/env python3
"""
Backtesting Runner CLI

Command-line interface for running backtests of the 9:30 breakout strategy.

Usage:
    python app/backtest_runner.py --symbols RELIANCE TCS --start 2024-01-01 --end 2024-12-31
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.backtester import Backtester
from app.config import CONFIG
from app.dhan_client import DhanHistoricalClient
from app.performance import PerformanceAnalyzer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("BacktestRunner")


def main():
    parser = argparse.ArgumentParser(
        description="Run backtests for 9:30 Breakout Strategy using Dhan API"
    )
    
    # Required arguments
    parser.add_argument(
        "--symbols",
        nargs="+",
        required=True,
        help="Stock symbols to backtest (e.g., RELIANCE TCS INFY)"
    )
    parser.add_argument(
        "--start-date",
        required=True,
        help="Start date in YYYY-MM-DD format"
    )
    parser.add_argument(
        "--end-date",
        required=True,
        help="End date in YYYY-MM-DD format"
    )
    
    # Optional arguments
    parser.add_argument(
        "--client-id",
        default=CONFIG.dhan_client_id,
        help="Dhan client ID (or set in config.py)"
    )
    parser.add_argument(
        "--access-token",
        default=CONFIG.dhan_access_token,
        help="Dhan access token (or set in config.py)"
    )
    parser.add_argument(
        "--capital",
        type=float,
        default=CONFIG.initial_capital,
        help=f"Initial capital (default: {CONFIG.initial_capital})"
    )
    parser.add_argument(
        "--risk-pct",
        type=float,
        default=CONFIG.max_risk_pct,
        help=f"Risk per trade as %% of equity (default: {CONFIG.max_risk_pct})"
    )
    parser.add_argument(
        "--risk-reward",
        type=float,
        default=CONFIG.risk_reward,
        help=f"Risk-reward ratio (default: {CONFIG.risk_reward})"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output CSV file for trade results"
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Don't use cached data, always fetch fresh from API"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose debug logging"
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate dates
    try:
        start_dt = datetime.strptime(args.start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(args.end_date, "%Y-%m-%d")
        if start_dt >= end_dt:
            logger.error("Start date must be before end date")
            return 1
    except ValueError as e:
        logger.error(f"Invalid date format: {e}")
        return 1
    
    # Validate credentials
    if not args.client_id or not args.access_token:
        logger.error("Dhan credentials not provided. Use --client-id and --access-token or set in config.py")
        return 1
    
    logger.info("="*60)
    logger.info("9:30 BREAKOUT STRATEGY BACKTESTER")
    logger.info("="*60)
    logger.info(f"Symbols:      {', '.join(args.symbols)}")
    logger.info(f"Date Range:   {args.start_date} to {args.end_date}")
    logger.info(f"Capital:      ₹{args.capital:,.2f}")
    logger.info(f"Risk/Trade:   {args.risk_pct:.2%}")
    logger.info(f"Risk/Reward:  1:{args.risk_reward}")
    logger.info("="*60)
    
    # Initialize Dhan client
    logger.info("\n📡 Initializing Dhan API client...")
    dhan_client = DhanHistoricalClient(
        client_id=args.client_id,
        access_token=args.access_token
    )
    
    # Fetch historical data
    logger.info("\n📊 Fetching historical data...")
    all_bars = []
    
    for symbol in args.symbols:
        logger.info(f"\nFetching {symbol}...")
        bars_df = dhan_client.fetch_historical_intraday(
            symbol=symbol,
            start_date=args.start_date,
            end_date=args.end_date,
            interval="1",  # 1-minute bars
            use_cache=not args.no_cache
        )
        
        if bars_df.empty:
            logger.warning(f"No data fetched for {symbol}, skipping...")
            continue
        
        all_bars.append(bars_df)
        logger.info(f"✓ {symbol}: {len(bars_df)} bars")
    
    if not all_bars:
        logger.error("No data available for backtesting")
        return 1
    
    # Combine all symbols
    combined_df = pd.concat(all_bars, ignore_index=True)
    combined_df = combined_df.sort_values('ts').reset_index(drop=True)
    
    logger.info(f"\n✓ Total bars loaded: {len(combined_df)}")
    
    # Run backtest
    logger.info("\n🔄 Running backtest...")
    backtester = Backtester(
        initial_capital=args.capital,
        max_risk_pct=args.risk_pct,
        risk_reward=args.risk_reward
    )
    
    results = backtester.run(combined_df)
    
    # Calculate performance metrics
    logger.info("\n📈 Calculating performance metrics...")
    metrics = PerformanceAnalyzer.calculate_metrics(results)
    
    # Print summary
    PerformanceAnalyzer.print_summary(metrics)
    
    # Save trades to CSV if requested
    if args.output:
        trades_df = pd.DataFrame(results["trades"])
        if not trades_df.empty:
            trades_df.to_csv(args.output, index=False)
            logger.info(f"\n💾 Trade results saved to: {args.output}")
        else:
            logger.warning("\n⚠️  No trades to save")
    
    logger.info("\n✅ Backtest complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
