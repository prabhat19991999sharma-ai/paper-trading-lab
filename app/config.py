from dataclasses import dataclass


import os

@dataclass
class AppConfig:
    # General
    timezone: str = "Asia/Kolkata"
    
    # Strategy
    breakout_time: str = "09:30:00"
    first_30_start: str = "09:15:00"
    first_30_end: str = "09:45:00"
    initial_capital: float = 100000.0
    max_risk_per_trade: float = 0.01
    reward_to_risk: float = 2.0
    min_r_value: float = 100.0
    
    # Broker (set one)
    broker_name: str = "dhan"  # "angel-one" or "dhan"
    
    # Angel One
    angel_api_key: str = os.getenv("ANGEL_API_KEY", "")
    angel_client_id: str = os.getenv("ANGEL_CLIENT_ID", "")
    angel_password: str = os.getenv("ANGEL_PASSWORD", "")
    angel_totp_key: str = os.getenv("ANGEL_TOTP_KEY", "")
    
    # Dhan
    dhan_client_id: str = os.getenv("DHAN_CLIENT_ID", "")
    dhan_access_token: str = os.getenv("DHAN_ACCESS_TOKEN", "")
    dhan_feed_version: str = os.getenv("DHAN_FEED_VERSION", "v2")
    dhan_feed_enabled: bool = os.getenv("DHAN_FEED_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
    
    # Trading Mode
    trading_mode: str = "PAPER"  # "PAPER" or "LIVE" - ALWAYS starts in PAPER mode
    require_confirmation: bool = True  # Require confirmation before placing orders in LIVE mode
    
    # Safety Limits
    max_trades_per_day: int = 5
    max_loss_per_day: float = 5000.0  # ₹5,000
    max_position_size: float = 10000.0  # ₹10,000 per trade
    max_positions_open: int = 3


CONFIG = AppConfig()
