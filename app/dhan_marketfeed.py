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
        self._lock = threading.Lock()
        self._connected = False
        self._status_message = "idle"
        self._status_level = "warn"
        self._status_time: Optional[str] = None
        self._last_error: Optional[str] = None
        self._last_tick_time: Optional[str] = None
        self._last_tick_symbol: Optional[str] = None
        self._last_tick_price: Optional[float] = None
        self._last_data_time: Optional[str] = None
        self._subscribed_symbols: Set[str] = set()
        self._invalid_symbols: List[str] = []

    def start(self, symbols: Iterable[str]) -> None:
        if self.running:
            return
        self.symbols = {s.upper() for s in symbols}
        self._set_status("starting", "warn")
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True, name="DhanMarketFeed")
        self.thread.start()

    def stop(self) -> None:
        self.running = False
        self._set_connected(False)
        self._set_status("stopped", "warn")

    def update_symbols(self, symbols: Iterable[str]) -> None:
        new_symbols = {s.upper() for s in symbols}
        added = new_symbols - self.symbols
        removed = self.symbols - new_symbols
        self.symbols = new_symbols

        # Update subscription tracking
        self._build_instruments(new_symbols, record=True)

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

        instruments = self._build_instruments(self.symbols, record=True)
        if not instruments:
            self._set_status("Dhan feed not started: no valid symbols found.", "danger")
            self.running = False
            return

        self.feed = DhanFeed(self.client_id, self.access_token, instruments, version=self.version)

        while self.running:
            try:
                self._set_status("connecting", "warn")
                self.feed.run_forever()
                self._set_connected(True)
                self._set_status("connected", "ok")

                while self.running:
                    data = self.feed.get_data()
                    self._set_last_data_time()
                    if getattr(self.feed, "on_close", False):
                        raise ConnectionError("Server disconnected")
                    if data:
                        self._handle_data(data)
            except Exception as exc:
                self._set_connected(False)
                self._set_error(str(exc))
                self._set_status(f"disconnected: {exc}", "danger")
                time.sleep(3)

        try:
            if self.feed:
                self.feed.close_connection()
        except Exception:
            pass

    def _build_instruments(
        self,
        symbols: Iterable[str],
        record: bool = False,
    ) -> List[Tuple[int, str]]:
        instruments: List[Tuple[int, str]] = []
        invalid: List[str] = []
        for symbol in symbols:
            token = self.security_map.get(symbol.upper())
            if token:
                instruments.append((marketfeed.NSE, str(token)))
            else:
                invalid.append(symbol.upper())
        if record:
            with self._lock:
                self._invalid_symbols = sorted(set(invalid))
                self._subscribed_symbols = {s.upper() for s in symbols if s.upper() not in self._invalid_symbols}
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
        self._set_last_tick(symbol, price, ts)
        try:
            self.on_tick(symbol, price, ts, 0.0)
        except Exception:
            pass

    def _set_status(self, message: str, level: str) -> None:
        if self.on_status:
            try:
                self.on_status(message)
            except Exception:
                pass
        with self._lock:
            self._status_message = message
            self._status_level = level
            self._status_time = datetime.now(self.tz).strftime("%Y-%m-%d %H:%M:%S")

    def _set_connected(self, value: bool) -> None:
        with self._lock:
            self._connected = value

    def _set_error(self, message: str) -> None:
        with self._lock:
            self._last_error = message

    def _set_last_tick(self, symbol: str, price: float, ts: str) -> None:
        with self._lock:
            self._last_tick_symbol = symbol
            self._last_tick_price = price
            self._last_tick_time = ts

    def _set_last_data_time(self) -> None:
        with self._lock:
            self._last_data_time = datetime.now(self.tz).strftime("%Y-%m-%d %H:%M:%S")

    def get_status(self) -> Dict[str, object]:
        with self._lock:
            return {
                "running": self.running,
                "connected": self._connected,
                "status_message": self._status_message,
                "status_level": self._status_level,
                "status_time": self._status_time,
                "last_error": self._last_error,
                "last_tick_time": self._last_tick_time,
                "last_tick_symbol": self._last_tick_symbol,
                "last_tick_price": self._last_tick_price,
                "last_data_time": self._last_data_time,
                "subscribed_symbols": sorted(self._subscribed_symbols),
                "subscribed_count": len(self._subscribed_symbols),
                "invalid_symbols": list(self._invalid_symbols),
                "version": self.version,
            }
