from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from typing import Optional

import pytz


@dataclass
class Trade:
    symbol: str
    side: str
    qty: float
    entry_time: str
    entry_price: float
    stop_loss: float
    target: float
    exit_time: Optional[str] = None
    exit_price: Optional[float] = None
    pnl: Optional[float] = None
    r_multiple: Optional[float] = None
    status: str = "open"


@dataclass
class DailyStats:
    trades: int = 0
    wins: int = 0
    losses: int = 0
    realized_pnl: float = 0.0
    r_total: float = 0.0

    @property
    def win_rate(self) -> float:
        return (self.wins / self.trades) if self.trades else 0.0

    @property
    def avg_r(self) -> float:
        return (self.r_total / self.trades) if self.trades else 0.0


@dataclass
class SymbolState:
    current_day: Optional[str] = None
    high_930: Optional[float] = None
    high_30: Optional[float] = None
    trades_today: int = 0
    open_trade: Optional[Trade] = None


def parse_dt(ts_str: str, tz: pytz.BaseTzInfo) -> datetime:
    ts_str = ts_str.strip()
    dt: datetime
    try:
        dt = datetime.fromisoformat(ts_str)
    except ValueError:
        try:
            dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M")

    if dt.tzinfo is None:
        dt = tz.localize(dt)
    else:
        dt = dt.astimezone(tz)
    return dt


def parse_time(hhmm: str) -> time:
    parts = hhmm.split(":")
    return time(int(parts[0]), int(parts[1]))
