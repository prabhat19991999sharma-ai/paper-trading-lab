from dataclasses import dataclass


import os

@dataclass(frozen=True)
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
    dhan_client_id: str = os.getenv("DHAN_CLIENT_ID", "1104713239")
    dhan_access_token: str = os.getenv("DHAN_ACCESS_TOKEN", "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJwX2lwIjoiIiwic19pcCI6IiIsImlzcyI6ImRoYW4iLCJwYXJ0bmVySWQiOiIiLCJleHAiOjE3NzA0MDU3NDIsImlhdCI6MTc3MDMxOTM0MiwidG9rZW5Db25zdW1lclR5cGUiOiJTRUxGIiwid2ViaG9va1VybCI6Imh0dHBzOi8vc2FuZGJveC5kaGFuLmNvL3YyIiwiZGhhbkNsaWVudElkIjoiMTEwNDcxMzIzOSJ9.WHGqdRcjcNuIDegjEOKEoOaYpyqmoNSPDrGPyacLXQPGj0T8WZTGJSI7cVTRSgveRqMzwCe6mcu7V3CJtyvvjA")
    
    # Trading Mode
    trading_mode: str = "PAPER"  # "PAPER" or "LIVE" - ALWAYS starts in PAPER mode
    require_confirmation: bool = True  # Require confirmation before placing orders in LIVE mode
    
    # Safety Limits
    max_trades_per_day: int = 5
    max_loss_per_day: float = 5000.0  # ₹5,000
    max_position_size: float = 10000.0  # ₹10,000 per trade
    max_positions_open: int = 3


CONFIG = AppConfig()
