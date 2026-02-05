from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    timezone: str = "Asia/Kolkata"
    session_open: str = "09:15"
    breakout_time: str = "09:30"
    first_30_start: str = "09:15"
    first_30_end: str = "09:45"
    risk_reward: float = 2.0
    initial_capital: float = 100000.0  # INR
    max_position_pct: float = 1.0  # use 100% of equity per trade
    max_risk_pct: float = 0.01  # risk per trade as % of equity
    max_trades_per_day_global: int = 5
    max_trades_per_day_per_symbol: int = 1
    max_daily_loss: float = -5000.0
    stop_fill_priority: str = "stop"  # "stop" or "target" when both hit in same bar

    # Broker Configuration
    broker_name: str = "paper"  # "paper", "angel-one", or "dhan"
    
    # Angel One
    angel_api_key: str = ""
    angel_client_id: str = ""
    angel_password: str = ""
    angel_totp_key: str = ""
    
    # Dhan
    dhan_client_id: str = "2602058043"
    dhan_access_token: str = "eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbkNvbnN1bWVyVHlwZSI6IlNFTEYiLCJwYXJ0bmVySWQiOiIiLCJkaGFuQ2xpZW50SWQiOiIyNjAyMDU4MDQzIiwid2ViaG9va1VybCI6Imh0dHBzOi8vYXBpLmRoYW4uY28vdjIiLCJpc3MiOiJkaGFuIiwiZXhwIjoxNzcwOTE3MjMzfQ.-MpDlASrh8WVbJtkwj2M-3IZ9LLwTl_YFC8D-cDaMtPwdOHYp1rWYqpvsyUZ94T1rVSuHdqpsxUY6ibUPOvIRA"


CONFIG = AppConfig()
