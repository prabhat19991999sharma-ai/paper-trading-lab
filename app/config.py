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
    broker_name: str = "paper"  # "paper" or "angel-one"
    angel_api_key: str = ""
    angel_client_id: str = ""
    angel_password: str = ""
    angel_totp_key: str = ""


CONFIG = AppConfig()
