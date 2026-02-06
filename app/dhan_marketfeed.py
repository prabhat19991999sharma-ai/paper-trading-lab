from __future__ import annotations

import asyncio
import threading
import time
from datetime import datetime
from typing import Callable, Dict, Iterable, List, Optional, Set, Tuple

import pytz
from dhanhq import marketfeed
from dhanhq.marketfeed import DhanFeed

TickCallback = Callable[[str, float, str, float], None]
StatusCallback = Optional[Callable[[str], None]]


class DhanMarketFeed:
    """Lightweight Dhan tick feed runner using dhanhq.marketfeed.DhanFeed (v1)."""

    def __init__(
        self,
        client_id: str,
        access_token: str,
        security_map: Dict[str, str],
        on_tick: TickCallback,
        timezone: str = "Asia/Kolkata",
        version: str = "v1",
        on_status: StatusCallback = None,
    ) -> None:
        self.client_id = client_id
        self.access_token = access_token
        self.security_map = security_map
        self.on_tick = on_tick
        self.on_status = on_status
        self.version = version
        self.tz = pytz.timezone(timezone)

        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.feed: Optional[DhanFeed] = None

        self.symbols: Set[str] = set()
        self.symbol_by_token: Dict[str, str] = {
            str(token): symbol.upper() for symbol, token in security_map.items()
        }

    def start(self, symbols: Iterable[str]) -> None:
        if self.running:
            return
        self.symbols = {s.upper() for s in symbols}
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True, name="DhanMarketFeed")
        self.thread.start()

    def stop(self) -> None:
        self.running = False

    def update_symbols(self, symbols: Iterable[str]) -> None:
        new_symbols = {s.upper() for s in symbols}
        added = new_symbols - self.symbols
        removed = self.symbols - new_symbols
        self.symbols = new_symbols

        if not self.feed or not self.running:
            return

        if added:
            added_instruments = self._build_instruments(added)
            if added_instruments:
                try:
                    self.feed.loop.call_soon_threadsafe(self.feed.subscribe_symbols, added_instruments)
                except Exception:
                    pass

        if removed:
            removed_instruments = self._build_instruments(removed)
            if removed_instruments:
                try:
                    self.feed.loop.call_soon_threadsafe(self.feed.unsubscribe_symbols, removed_instruments)
                except Exception:
                    pass

    def _run(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        instruments = self._build_instruments(self.symbols)
        if not instruments:
            self._status("Dhan feed not started: no valid symbols found.")
            self.running = False
            return

        self.feed = DhanFeed(self.client_id, self.access_token, instruments, version=self.version)

        while self.running:
            try:
                self.feed.run_forever()
                self._status("Dhan feed connected.")

                while self.running:
                    data = self.feed.get_data()
                    if data:
                        self._handle_data(data)
            except Exception as exc:
                self._status(f"Dhan feed error: {exc}")
                time.sleep(3)

        try:
            if self.feed:
                self.feed.close_connection()
        except Exception:
            pass

    def _build_instruments(self, symbols: Iterable[str]) -> List[Tuple[int, str]]:
        instruments: List[Tuple[int, str]] = []
        for symbol in symbols:
            token = self.security_map.get(symbol.upper())
            if token:
                instruments.append((marketfeed.NSE, str(token)))
        return instruments

    def _handle_data(self, data: object) -> None:
        if not isinstance(data, dict):
            return

        security_id = data.get("security_id")
        if security_id is None:
            return

        symbol = self.symbol_by_token.get(str(security_id))
        if not symbol:
            return

        ltp_raw = data.get("LTP")
        if ltp_raw is None:
            return

        try:
            price = float(ltp_raw)
        except (TypeError, ValueError):
            return

        ts = datetime.now(self.tz).strftime("%Y-%m-%d %H:%M:%S")
        try:
            self.on_tick(symbol, price, ts, 0.0)
        except Exception:
            pass

    def _status(self, message: str) -> None:
        if self.on_status:
            try:
                self.on_status(message)
            except Exception:
                pass
