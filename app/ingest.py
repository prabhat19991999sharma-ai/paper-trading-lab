from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

import pytz

from .db import get_connection
from .strategy_core import parse_dt


@dataclass
class Bar:
    ts: str
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class BarAggregator:
    def __init__(self, tz: pytz.BaseTzInfo) -> None:
        self.tz = tz
        self.current_bar: Dict[str, Bar] = {}
        self.current_bucket: Dict[str, datetime] = {}

    def ingest_tick(self, ts: str, symbol: str, price: float, volume: float = 0.0) -> Optional[Bar]:
        dt = parse_dt(ts, self.tz)
        bucket = dt.replace(second=0, microsecond=0)
        current_bucket = self.current_bucket.get(symbol)

        if current_bucket is None:
            self.current_bucket[symbol] = bucket
            self.current_bar[symbol] = Bar(
                ts=bucket.strftime("%Y-%m-%d %H:%M"),
                symbol=symbol,
                open=price,
                high=price,
                low=price,
                close=price,
                volume=volume,
            )
            return None

        if bucket == current_bucket:
            bar = self.current_bar[symbol]
            bar.high = max(bar.high, price)
            bar.low = min(bar.low, price)
            bar.close = price
            bar.volume += volume
            return None

        if bucket > current_bucket:
            completed = self.current_bar[symbol]
            self.current_bucket[symbol] = bucket
            self.current_bar[symbol] = Bar(
                ts=bucket.strftime("%Y-%m-%d %H:%M"),
                symbol=symbol,
                open=price,
                high=price,
                low=price,
                close=price,
                volume=volume,
            )
            return completed

        return None

    def flush(self) -> Dict[str, Bar]:
        completed = dict(self.current_bar)
        self.current_bar.clear()
        self.current_bucket.clear()
        return completed


def insert_bar(bar: Bar) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR IGNORE INTO bars (ts, symbol, open, high, low, close, volume)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """,
        (bar.ts, bar.symbol, bar.open, bar.high, bar.low, bar.close, bar.volume),
    )
    conn.commit()
    conn.close()
