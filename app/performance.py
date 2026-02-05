"""
Performance Metrics Calculator for Backtesting

Calculates advanced performance metrics including:
- Returns (total, annualized)
- Risk metrics (Sharpe, Sortino, Max Drawdown)
- Trade statistics
"""

import logging
from datetime import datetime
from typing import Dict, List

import numpy as np
import pandas as pd

logger = logging.getLogger("Performance")


class PerformanceAnalyzer:
    """Calculate performance metrics from backtest results"""
    
    @staticmethod
    def calculate_metrics(backtest_results: Dict) -> Dict:
        """
        Calculate comprehensive performance metrics
        
        Args:
            backtest_results: Results dictionary from Backtester.get_results()
            
        Returns:
            Dictionary with performance metrics
        """
        trades = backtest_results.get("trades", [])
        equity_curve = backtest_results.get("equity_curve", [])
        initial_capital = backtest_results.get("initial_capital", 100000)
        final_equity = backtest_results.get("final_equity", initial_capital)
        
        if not trades:
            return {
                "total_trades": 0,
                "error": "No trades to analyze"
            }
        
        # Basic metrics
        total_trades = len(trades)
        wins = sum(1 for t in trades if t.get("pnl", 0) >= 0)
        losses = total_trades - wins
        win_rate = wins / total_trades if total_trades > 0 else 0
        
        pnls = [t.get("pnl", 0) for t in trades]
        r_multiples = [t.get("r_multiple", 0) for t in trades if t.get("r_multiple")]
        
        total_pnl = sum(pnls)
        total_return_pct = (total_pnl / initial_capital) * 100
        
        # Win/Loss statistics
        winning_trades = [p for p in pnls if p >= 0]
        losing_trades = [p for p in pnls if p < 0]
        
        avg_win = np.mean(winning_trades) if winning_trades else 0
        avg_loss = np.mean(losing_trades) if losing_trades else 0
        max_win = max(winning_trades) if winning_trades else 0
        max_loss = min(losing_trades) if losing_trades else 0
        
        profit_factor = (sum(winning_trades) / abs(sum(losing_trades))) if losing_trades else 0
        
        # R-multiple statistics
        avg_r = np.mean(r_multiples) if r_multiples else 0
        
        # Calculate drawdown from equity curve
        max_drawdown, max_drawdown_pct = PerformanceAnalyzer._calculate_max_drawdown(equity_curve)
        
        # Annualized metrics (if we have date info)
        annualized_return = PerformanceAnalyzer._calculate_annualized_return(
            trades, total_return_pct
        )
        
        # Risk-adjusted metrics
        sharpe_ratio = PerformanceAnalyzer._calculate_sharpe_ratio(pnls, initial_capital)
        sortino_ratio = PerformanceAnalyzer._calculate_sortino_ratio(pnls, initial_capital)
        
        # Monthly breakdown
        monthly_stats = PerformanceAnalyzer._calculate_monthly_stats(trades)
        
        return {
            # Trade statistics
            "total_trades": total_trades,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            
            # Return metrics
            "initial_capital": initial_capital,
            "final_equity": final_equity,
            "total_return": total_pnl,
            "total_return_pct": total_return_pct,
            "annualized_return_pct": annualized_return,
            
            # Win/Loss metrics
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "max_win": max_win,
            "max_loss": max_loss,
            "profit_factor": profit_factor,
            
            # R-multiple metrics
            "avg_r": avg_r,
            
            # Risk metrics
            "max_drawdown": max_drawdown,
            "max_drawdown_pct": max_drawdown_pct,
            "sharpe_ratio": sharpe_ratio,
            "sortino_ratio": sortino_ratio,
            
            # Breakdown
            "monthly_stats": monthly_stats
        }
    
    @staticmethod
    def _calculate_max_drawdown(equity_curve: List[Dict]) -> tuple:
        """Calculate maximum drawdown from equity curve"""
        if not equity_curve:
            return 0, 0
        
        equities = [point["equity"] for point in equity_curve]
        peak = equities[0]
        max_dd = 0
        max_dd_pct = 0
        
        for equity in equities:
            if equity > peak:
                peak = equity
            dd = peak - equity
            dd_pct = (dd / peak) * 100 if peak > 0 else 0
            max_dd = max(max_dd, dd)
            max_dd_pct = max(max_dd_pct, dd_pct)
        
        return max_dd, max_dd_pct
    
    @staticmethod
    def _calculate_annualized_return(trades: List[Dict], total_return_pct: float) -> float:
        """Calculate annualized return"""
        if not trades:
            return 0
        
        try:
            # Get first and last trade dates
            first_date = datetime.fromisoformat(trades[0]["entry_time"])
            last_date = datetime.fromisoformat(trades[-1]["exit_time"])
            
            days = (last_date - first_date).days
            if days == 0:
                return 0
            
            years = days / 365.25
            if years == 0:
                return 0
            
            # Annualized return = (1 + total_return)^(1/years) - 1
            annualized = ((1 + total_return_pct / 100) ** (1 / years) - 1) * 100
            return annualized
        except (KeyError, ValueError, ZeroDivisionError):
            return 0
    
    @staticmethod
    def _calculate_sharpe_ratio(pnls: List[float], initial_capital: float) -> float:
        """Calculate Sharpe ratio (annualized, risk-free rate = 0)"""
        if not pnls or len(pnls) < 2:
            return 0
        
        # Convert PnLs to returns
        returns = [(pnl / initial_capital) for pnl in pnls]
        
        avg_return = np.mean(returns)
        std_return = np.std(returns, ddof=1)
        
        if std_return == 0:
            return 0
        
        # Annualize (assuming ~252 trading days, but we trade less frequently)
        # Simplified: use sqrt(number of trades per year)
        trades_per_year = 252  # Assume daily frequency
        sharpe = (avg_return / std_return) * np.sqrt(trades_per_year)
        
        return sharpe
    
    @staticmethod
    def _calculate_sortino_ratio(pnls: List[float], initial_capital: float) -> float:
        """Calculate Sortino ratio (downside deviation only)"""
        if not pnls or len(pnls) < 2:
            return 0
        
        returns = [(pnl / initial_capital) for pnl in pnls]
        avg_return = np.mean(returns)
        
        # Downside deviation (only negative returns)
        downside_returns = [r for r in returns if r < 0]
        if not downside_returns:
            return 0
        
        downside_std = np.std(downside_returns, ddof=1)
        if downside_std == 0:
            return 0
        
        trades_per_year = 252
        sortino = (avg_return / downside_std) * np.sqrt(trades_per_year)
        
        return sortino
    
    @staticmethod
    def _calculate_monthly_stats(trades: List[Dict]) -> Dict:
        """Calculate monthly performance breakdown"""
        monthly_pnl = {}
        
        for trade in trades:
            try:
                exit_time = datetime.fromisoformat(trade["exit_time"])
                month_key = exit_time.strftime("%Y-%m")
                
                if month_key not in monthly_pnl:
                    monthly_pnl[month_key] = 0
                
                monthly_pnl[month_key] += trade.get("pnl", 0)
            except (KeyError, ValueError):
                continue
        
        return monthly_pnl
    
    @staticmethod
    def print_summary(metrics: Dict):
        """Print formatted performance summary"""
        print("\n" + "="*60)
        print("BACKTEST PERFORMANCE SUMMARY")
        print("="*60)
        
        # Trade Statistics
        print(f"\n📊 Trade Statistics:")
        print(f"  Total Trades:     {metrics.get('total_trades', 0)}")
        print(f"  Wins:             {metrics.get('wins', 0)}")
        print(f"  Losses:           {metrics.get('losses', 0)}")
        print(f"  Win Rate:         {metrics.get('win_rate', 0):.2%}")
        
        # Returns
        print(f"\n💰 Returns:")
        print(f"  Initial Capital:  ₹{metrics.get('initial_capital', 0):,.2f}")
        print(f"  Final Equity:     ₹{metrics.get('final_equity', 0):,.2f}")
        print(f"  Total Return:     ₹{metrics.get('total_return', 0):,.2f}")
        print(f"  Return %:         {metrics.get('total_return_pct', 0):.2f}%")
        print(f"  Annualized %:     {metrics.get('annualized_return_pct', 0):.2f}%")
        
        # Win/Loss
        print(f"\n📈 Win/Loss Analysis:")
        print(f"  Avg Win:          ₹{metrics.get('avg_win', 0):,.2f}")
        print(f"  Avg Loss:         ₹{metrics.get('avg_loss', 0):,.2f}")
        print(f"  Max Win:          ₹{metrics.get('max_win', 0):,.2f}")
        print(f"  Max Loss:         ₹{metrics.get('max_loss', 0):,.2f}")
        print(f"  Profit Factor:    {metrics.get('profit_factor', 0):.2f}")
        
        # Risk Metrics
        print(f"\n⚠️  Risk Metrics:")
        print(f"  Avg R-Multiple:   {metrics.get('avg_r', 0):.2f}R")
        print(f"  Max Drawdown:     ₹{metrics.get('max_drawdown', 0):,.2f}")
        print(f"  Max Drawdown %:   {metrics.get('max_drawdown_pct', 0):.2f}%")
        print(f"  Sharpe Ratio:     {metrics.get('sharpe_ratio', 0):.2f}")
        print(f"  Sortino Ratio:    {metrics.get('sortino_ratio', 0):.2f}")
        
        # Monthly breakdown
        monthly = metrics.get('monthly_stats', {})
        if monthly:
            print(f"\n📅 Monthly Breakdown:")
            for month, pnl in sorted(monthly.items()):
                print(f"  {month}:  ₹{pnl:,.2f}")
        
        print("\n" + "="*60)
