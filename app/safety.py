"""
Safety and Risk Management Module for Live Trading
"""
import logging
from dataclasses import dataclass
from datetime import datetime, time as time_type
from typing import Optional

import pytz


@dataclass
class SafetyLimits:
    """Safety limits configuration"""
    max_trades_per_day: int = 5
    max_loss_per_day: float = 5000.0
    max_position_size: float = 10000.0
    max_positions_open: int = 3
    trading_start_time: time_type = time_type(9, 15)
    trading_end_time: time_type = time_type(15, 30)


class SafetyManager:
    """Manages trading safety controls and risk limits"""
    
    def __init__(self, limits: SafetyLimits, timezone: str = "Asia/Kolkata"):
        self.limits = limits
        self.tz = pytz.timezone(timezone)
        self.logger = logging.getLogger("SafetyManager")
        
        # State tracking
        self.kill_switch_active = False
        self.trades_today = 0
        self.loss_today = 0.0
        self.open_positions = 0
        self.last_reset_date: Optional[str] = None
        
    def reset_daily_counters(self):
        """Reset counters at start of new trading day"""
        today = datetime.now(self.tz).strftime("%Y-%m-%d")
        if self.last_reset_date != today:
            self.trades_today = 0
            self.loss_today = 0.0
            self.last_reset_date = today
            self.logger.info(f"Daily counters reset for {today}")
    
    def is_trading_allowed(self) -> tuple[bool, str]:
        """
        Check if trading is allowed based on all safety criteria
        Returns: (allowed: bool, reason: str)
        """
        self.reset_daily_counters()
        
        # Check kill switch
        if self.kill_switch_active:
            return False, "Kill switch is active"
        
        # Check trading hours
        now = datetime.now(self.tz).time()
        if not (self.limits.trading_start_time <= now <= self.limits.trading_end_time):
            return False, f"Outside trading hours ({self.limits.trading_start_time} - {self.limits.trading_end_time})"
        
        # Check daily trade limit
        if self.trades_today >= self.limits.max_trades_per_day:
            return False, f"Daily trade limit reached ({self.limits.max_trades_per_day})"
        
        # Check daily loss limit
        if self.loss_today >= self.limits.max_loss_per_day:
            return False, f"Daily loss limit reached (₹{self.limits.max_loss_per_day:,.2f})"
        
        # Check open positions
        if self.open_positions >= self.limits.max_positions_open:
            return False, f"Maximum open positions reached ({self.limits.max_positions_open})"
        
        return True, "Trading allowed"
    
    def validate_position_size(self, position_value: float) -> tuple[bool, str]:
        """Validate position size against limits"""
        if position_value > self.limits.max_position_size:
            return False, f"Position size (₹{position_value:,.2f}) exceeds limit (₹{self.limits.max_position_size:,.2f})"
        return True, "Position size OK"
    
    def record_trade(self, pnl: float = 0.0):
        """Record a trade execution"""
        self.reset_daily_counters()
        self.trades_today += 1
        if pnl < 0:
            self.loss_today += abs(pnl)
        self.logger.info(f"Trade recorded. Today: {self.trades_today} trades, ₹{self.loss_today:,.2f} loss")
    
    def record_position_open(self):
        """Record a position being opened"""
        self.open_positions += 1
        self.logger.info(f"Position opened. Total open: {self.open_positions}")
    
    def record_position_close(self):
        """Record a position being closed"""
        if self.open_positions > 0:
            self.open_positions -= 1
        self.logger.info(f"Position closed. Total open: {self.open_positions}")
    
    def activate_kill_switch(self):
        """Activate emergency kill switch"""
        self.kill_switch_active = True
        self.logger.critical("🚨 KILL SWITCH ACTIVATED - All trading stopped")
    
    def deactivate_kill_switch(self):
        """Deactivate kill switch"""
        self.kill_switch_active = False
        self.logger.info("Kill switch deactivated - Trading can resume")
    
    def get_status(self) -> dict:
        """Get current safety status"""
        self.reset_daily_counters()
        allowed, reason = self.is_trading_allowed()
        
        return {
            "trading_allowed": allowed,
            "status_message": reason,
            "kill_switch_active": self.kill_switch_active,
            "trades_today": self.trades_today,
            "trades_remaining": max(0, self.limits.max_trades_per_day - self.trades_today),
            "loss_today": self.loss_today,
            "loss_remaining": max(0, self.limits.max_loss_per_day - self.loss_today),
            "open_positions": self.open_positions,
            "positions_remaining": max(0, self.limits.max_positions_open - self.open_positions),
            "limits": {
                "max_trades_per_day": self.limits.max_trades_per_day,
                "max_loss_per_day": self.limits.max_loss_per_day,
                "max_position_size": self.limits.max_position_size,
                "max_positions_open": self.limits.max_positions_open
            }
        }
