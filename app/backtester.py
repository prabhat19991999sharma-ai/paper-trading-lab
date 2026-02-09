"""
Backtesting Engine for 9:30 Breakout Strategy

Simulates the strategy on historical data to evaluate performance.
Reuses strategy logic from live_engine.py for consistency.
"""

import logging
from dataclasses import asdict
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
import pytz

from .config import CONFIG
from .strategy_core import DailyStats, SymbolState, Trade, parse_dt, parse_time

logger = logging.getLogger("Backtester")


class Backtester:
    """Backtesting engine for the 9:30 breakout strategy"""
    
    def __init__(
        self,
        initial_capital: float = None,
        max_risk_pct: float = None,
        risk_reward: float = None
    ):
        """
        Initialize backtester
        
        Args:
            initial_capital: Starting capital (default from CONFIG)
            max_risk_pct: Max risk per trade as % of equity (default from CONFIG)
            risk_reward: Risk-reward ratio (default from CONFIG)
        """
        self.initial_capital = initial_capital or CONFIG.initial_capital
        self.max_risk_pct = max_risk_pct or CONFIG.max_risk_pct
        self.risk_reward = risk_reward or CONFIG.risk_reward
        
        # State tracking
        self.equity = self.initial_capital
        self.state_by_symbol: Dict[str, SymbolState] = {}
        self.daily_stats: Dict[str, DailyStats] = {}
        self.trades: List[Trade] = []
        self.equity_curve: List[Dict] = []
        
        # Strategy parameters
        self.tz = pytz.timezone(CONFIG.timezone)
        self.breakout_time = parse_time(CONFIG.breakout_time)
        self.first_30_start = parse_time(CONFIG.first_30_start)
        self.first_30_end = parse_time(CONFIG.first_30_end)
        
        logger.info(f"Backtester initialized with capital: ₹{self.initial_capital:,.2f}")
    
    def _risk_limited_qty(self, entry_price: float, stop_loss: float) -> int:
        """
        Calculate position size based on risk management rules
        
        Same logic as live_engine.py to ensure consistency
        """
        risk_per_share = entry_price - stop_loss
        if risk_per_share <= 0:
            return 0
        
        qty_by_equity = int((self.equity * CONFIG.max_position_pct) / entry_price)
        if self.max_risk_pct <= 0:
            return qty_by_equity
        
        max_risk = self.equity * self.max_risk_pct
        qty_by_risk = int(max_risk / risk_per_share)
        return max(0, min(qty_by_equity, qty_by_risk))
    
    def _process_bar(self, bar: dict) -> Optional[Trade]:
        """
        Process a single bar and execute strategy logic
        
        Returns completed trade if any
        """
        symbol = bar["symbol"]
        state = self.state_by_symbol.setdefault(symbol, SymbolState())
        
        # Parse timestamp
        if isinstance(bar["ts"], str):
            dt = parse_dt(bar["ts"], self.tz)
        else:
            dt = bar["ts"]
            if dt.tzinfo is None:
                dt = self.tz.localize(dt)
        
        local_date = dt.strftime("%Y-%m-%d")
        local_time = dt.time()
        
        # Reset daily state
        if state.current_day != local_date:
            state.current_day = local_date
            state.high_930 = None
            state.high_30 = None
            state.trades_today = 0
            state.open_trade = None
        
        # Get or create daily stats
        stats = self.daily_stats.setdefault(local_date, DailyStats())
        
        # Check global limits
        if stats.trades >= CONFIG.max_trades_per_day_global:
            return None
        if stats.realized_pnl <= CONFIG.max_daily_loss:
            return None
        
        # === CAPTURE 9:15-09:30 HIGH ===
        if self.first_30_start <= local_time <= self.first_30_end:
            if state.high_30 is None:
                state.high_30 = float(bar["high"])
            else:
                state.high_30 = max(state.high_30, float(bar["high"]))

        # === ENTRY LOGIC (after 09:30) ===
        if state.open_trade is None and state.high_30 and local_time > self.breakout_time:
            if (state.trades_today < CONFIG.max_trades_per_day_per_symbol and
                float(bar["close"]) > state.high_30):
                
                entry_price = float(bar["close"])
                stop_loss = float(bar["low"])
                qty = self._risk_limited_qty(entry_price, stop_loss)
                
                if qty > 0:
                    risk = entry_price - stop_loss
                    target = entry_price + risk * self.risk_reward
                    
                    state.open_trade = Trade(
                        symbol=symbol,
                        side="LONG",
                        qty=qty,
                        entry_time=dt.isoformat(),
                        entry_price=entry_price,
                        stop_loss=stop_loss,
                        target=target,
                    )
                    state.trades_today += 1
                    logger.debug(f"Entry: {symbol} @ {entry_price:.2f}, SL: {stop_loss:.2f}, Target: {target:.2f}, Qty: {qty}")
        
        # === EXIT LOGIC ===
        if state.open_trade is not None:
            low = float(bar["low"])
            high = float(bar["high"])
            stop_hit = low <= state.open_trade.stop_loss
            target_hit = high >= state.open_trade.target
            
            exit_price = None
            if stop_hit and target_hit:
                # Both hit in same bar - use priority from config
                exit_price = (state.open_trade.stop_loss if CONFIG.stop_fill_priority == "stop" 
                            else state.open_trade.target)
            elif stop_hit:
                exit_price = state.open_trade.stop_loss
            elif target_hit:
                exit_price = state.open_trade.target
            
            if exit_price is not None:
                state.open_trade.exit_time = dt.isoformat()
                state.open_trade.exit_price = exit_price
                state.open_trade.pnl = (exit_price - state.open_trade.entry_price) * state.open_trade.qty
                state.open_trade.r_multiple = ((exit_price - state.open_trade.entry_price) / 
                                               (state.open_trade.entry_price - state.open_trade.stop_loss))
                state.open_trade.status = "closed"
                
                # Update stats
                stats.trades += 1
                stats.realized_pnl += state.open_trade.pnl
                stats.r_total += state.open_trade.r_multiple
                self.equity += state.open_trade.pnl
                
                if state.open_trade.pnl >= 0:
                    stats.wins += 1
                else:
                    stats.losses += 1
                
                logger.debug(f"Exit: {symbol} @ {exit_price:.2f}, PnL: ₹{state.open_trade.pnl:,.2f}, R: {state.open_trade.r_multiple:.2f}")
                
                # Store trade
                completed_trade = state.open_trade
                self.trades.append(completed_trade)
                state.open_trade = None
                
                return completed_trade
        
        return None
    
    def run(self, bars_df: pd.DataFrame) -> Dict:
        """
        Run backtest on historical data
        
        Args:
            bars_df: DataFrame with columns: ts, symbol, open, high, low, close, volume
            
        Returns:
            Dictionary with backtest results
        """
        logger.info(f"Starting backtest on {len(bars_df)} bars")
        
        # Reset state
        self.equity = self.initial_capital
        self.state_by_symbol.clear()
        self.daily_stats.clear()
        self.trades.clear()
        self.equity_curve.clear()
        
        # Ensure timestamp column is datetime
        if not pd.api.types.is_datetime64_any_dtype(bars_df['ts']):
            bars_df['ts'] = pd.to_datetime(bars_df['ts'])
        
        # Sort by timestamp
        bars_df = bars_df.sort_values('ts').reset_index(drop=True)
        
        # Process each bar
        for idx, row in bars_df.iterrows():
            bar = row.to_dict()
            self._process_bar(bar)
            
            # Track equity curve (sample every 100 bars to reduce memory)
            if idx % 100 == 0:
                self.equity_curve.append({
                    'ts': row['ts'],
                    'equity': self.equity
                })
        
        # Final equity point
        if len(bars_df) > 0:
            self.equity_curve.append({
                'ts': bars_df.iloc[-1]['ts'],
                'equity': self.equity
            })
        
        logger.info(f"Backtest complete: {len(self.trades)} trades, Final equity: ₹{self.equity:,.2f}")
        
        return self.get_results()
    
    def get_results(self) -> Dict:
        """Get backtest results summary"""
        total_trades = len(self.trades)
        
        if total_trades == 0:
            return {
                "total_trades": 0,
                "initial_capital": self.initial_capital,
                "final_equity": self.equity,
                "total_return": 0.0,
                "total_return_pct": 0.0,
                "win_rate": 0.0,
                "avg_r": 0.0,
                "trades": [],
                "equity_curve": self.equity_curve
            }
        
        wins = sum(1 for t in self.trades if t.pnl and t.pnl >= 0)
        losses = total_trades - wins
        total_pnl = sum(t.pnl for t in self.trades if t.pnl)
        avg_r = sum(t.r_multiple for t in self.trades if t.r_multiple) / total_trades
        
        return {
            "total_trades": total_trades,
            "wins": wins,
            "losses": losses,
            "win_rate": wins / total_trades if total_trades > 0 else 0,
            "initial_capital": self.initial_capital,
            "final_equity": self.equity,
            "total_return": total_pnl,
            "total_return_pct": (total_pnl / self.initial_capital) * 100,
            "avg_r": avg_r,
            "trades": [asdict(t) for t in self.trades],
            "equity_curve": self.equity_curve,
            "daily_stats": {date: asdict(stats) for date, stats in self.daily_stats.items()}
        }
