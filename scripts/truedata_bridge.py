import os
import sys
import time
from datetime import datetime, timedelta

import requests

try:
    from truedata import TD_live
except ImportError as exc:
    raise SystemExit(
        "Missing dependency 'truedata'. Install with: pip install truedata"
    ) from exc


INGEST_BASE_URL = os.getenv("INGEST_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
WATCHLIST_URL = os.getenv("WATCHLIST_URL", f"{INGEST_BASE_URL}/api/watchlist")
TRUEDATA_USERNAME = os.getenv("TRUEDATA_USERNAME")
TRUEDATA_PASSWORD = os.getenv("TRUEDATA_PASSWORD")
TRUEDATA_SYMBOLS = os.getenv("TRUEDATA_SYMBOLS", "")
TRUEDATA_MODE = os.getenv("TRUEDATA_MODE", "ticks").lower()
TRUEDATA_LIVE_PORT = os.getenv("TRUEDATA_LIVE_PORT")
TRUEDATA_URL = os.getenv("TRUEDATA_URL")
WATCHLIST_POLL = float(os.getenv("TRUEDATA_WATCHLIST_POLL", "30"))
STALE_AFTER = float(os.getenv("TRUEDATA_STALE_AFTER", "30"))
BACKFILL_MINUTES = int(os.getenv("TRUEDATA_BACKFILL_MINUTES", "5"))
RECONNECT_BACKOFF = float(os.getenv("TRUEDATA_RECONNECT_BACKOFF", "5"))

TICK_ENDPOINT = f"{INGEST_BASE_URL}/api/ingest/tick"
BAR_ENDPOINT = f"{INGEST_BASE_URL}/api/ingest/bar"


class BridgeState:
    def __init__(self) -> None:
        self.last_event = time.monotonic()
        self.last_seen_by_symbol = {}

    def mark_event(self, symbol: str, ts: datetime) -> None:
        self.last_event = time.monotonic()
        self.last_seen_by_symbol[symbol] = ts


def _as_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _parse_ts(value) -> datetime:
    if hasattr(value, "to_pydatetime"):
        return value.to_pydatetime()
    if hasattr(value, "strftime"):
        return value
    if isinstance(value, (int, float)):
        epoch = value
        if epoch > 1e12:
            epoch = epoch / 1000.0
        return datetime.fromtimestamp(epoch)
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
    return datetime.utcnow()


def _format_ts(value) -> str:
    return _parse_ts(value).strftime("%Y-%m-%d %H:%M:%S")


def _post_json(url: str, payload: dict) -> None:
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as exc:
        print(f"Failed to post to {url}: {exc}")


def _require_env() -> None:
    if not TRUEDATA_USERNAME or not TRUEDATA_PASSWORD:
        raise SystemExit("Set TRUEDATA_USERNAME and TRUEDATA_PASSWORD env vars first")


def _build_td() -> TD_live:
    kwargs = {}
    if TRUEDATA_LIVE_PORT:
        try:
            kwargs["live_port"] = int(TRUEDATA_LIVE_PORT)
        except ValueError:
            raise SystemExit("TRUEDATA_LIVE_PORT must be an integer")
    if TRUEDATA_URL:
        kwargs["url"] = TRUEDATA_URL
    return TD_live(TRUEDATA_USERNAME, TRUEDATA_PASSWORD, **kwargs)


def _fetch_watchlist() -> list[str]:
    if TRUEDATA_SYMBOLS.strip():
        return [s.strip().upper() for s in TRUEDATA_SYMBOLS.split(",") if s.strip()]
    try:
        resp = requests.get(WATCHLIST_URL, timeout=5)
        data = resp.json()
        symbols = data.get("symbols", [])
        return [str(s).upper() for s in symbols if str(s).strip()]
    except Exception as exc:
        print(f"Failed to fetch watchlist: {exc}")
        return []


def _extract_value(row, keys):
    if isinstance(row, dict):
        for key in keys:
            if key in row:
                return row[key]
        return None
    if hasattr(row, "get"):
        for key in keys:
            value = row.get(key)
            if value is not None:
                return value
    for key in keys:
        if hasattr(row, key):
            return getattr(row, key)
    return None


def _iter_hist_rows(hist):
    if hist is None:
        return []
    if hasattr(hist, "iterrows"):
        for _, row in hist.iterrows():
            yield row
        return
    if isinstance(hist, list):
        for row in hist:
            yield row
        return
    if isinstance(hist, dict):
        data = hist.get("data") if hasattr(hist, "get") else None
        if isinstance(data, list):
            for row in data:
                yield row


def _backfill(td_obj, symbols, last_seen_by_symbol):
    if BACKFILL_MINUTES <= 0:
        return
    if not hasattr(td_obj, "get_historic_data"):
        return

    cutoff = datetime.utcnow() - timedelta(minutes=BACKFILL_MINUTES)
    for symbol in symbols:
        last_seen = last_seen_by_symbol.get(symbol)
        if not last_seen:
            continue
        try:
            hist = td_obj.get_historic_data(symbol, duration="1 D", bar_size="1 min")
        except Exception as exc:
            print(f"Backfill failed for {symbol}: {exc}")
            continue

        for row in _iter_hist_rows(hist):
            ts = _extract_value(row, ["timestamp", "time", "t", "date", "datetime"]) or _extract_value(row, ["ts"])
            if ts is None:
                continue
            ts_dt = _parse_ts(ts)
            if ts_dt <= last_seen or ts_dt < cutoff:
                continue

            payload = {
                "ts": _format_ts(ts_dt),
                "symbol": symbol,
                "open": _as_float(_extract_value(row, ["open", "o"])),
                "high": _as_float(_extract_value(row, ["high", "h"])),
                "low": _as_float(_extract_value(row, ["low", "l"])),
                "close": _as_float(_extract_value(row, ["close", "c"])),
                "volume": _as_float(_extract_value(row, ["volume", "v", "vol"])),
            }
            if payload["open"] == payload["close"] == payload["high"] == payload["low"] == 0:
                continue
            _post_json(BAR_ENDPOINT, payload)


def _register_callbacks(td_obj, state: BridgeState):
    if TRUEDATA_MODE in {"ticks", "both"}:
        if hasattr(td_obj, "trade_callback"):
            @td_obj.trade_callback
            def on_tick(tick_data):
                symbol = str(getattr(tick_data, "symbol", "")).upper()
                if not symbol:
                    return
                ts = getattr(tick_data, "timestamp", datetime.utcnow())
                payload = {
                    "ts": _format_ts(ts),
                    "symbol": symbol,
                    "price": _as_float(getattr(tick_data, "ltp", 0.0)),
                    "volume": _as_float(getattr(tick_data, "ltq", 0.0)),
                }
                state.mark_event(symbol, _parse_ts(ts))
                _post_json(TICK_ENDPOINT, payload)
        else:
            print("trade_callback not available in this TrueData client.")

    if TRUEDATA_MODE in {"one_min", "bars", "both"}:
        if hasattr(td_obj, "one_min_bar_callback"):
            @td_obj.one_min_bar_callback
            def on_bar(bar_data):
                symbol = str(getattr(bar_data, "symbol", "")).upper()
                if not symbol:
                    return
                ts = getattr(bar_data, "timestamp", datetime.utcnow())
                payload = {
                    "ts": _format_ts(ts),
                    "symbol": symbol,
                    "open": _as_float(getattr(bar_data, "open", 0.0)),
                    "high": _as_float(getattr(bar_data, "high", 0.0)),
                    "low": _as_float(getattr(bar_data, "low", 0.0)),
                    "close": _as_float(getattr(bar_data, "close", 0.0)),
                    "volume": _as_float(getattr(bar_data, "volume", 0.0)),
                }
                state.mark_event(symbol, _parse_ts(ts))
                _post_json(BAR_ENDPOINT, payload)
        else:
            print("one_min_bar_callback not available in this TrueData client.")


def _start_stream(td_obj, symbols: list[str]) -> None:
    td_obj.start_live_data(symbols)
    print("TrueData stream started for:", ", ".join(symbols))


def _stop_stream(td_obj, symbols: list[str]) -> None:
    try:
        td_obj.stop_live_data(symbols)
    except Exception:
        pass
    try:
        td_obj.disconnect()
    except Exception:
        pass


def main() -> None:
    _require_env()
    while True:
        symbols = _fetch_watchlist()
        if not symbols:
            print("No symbols found. Waiting...")
            time.sleep(RECONNECT_BACKOFF)
            continue

        td_obj = _build_td()
        state = BridgeState()
        _register_callbacks(td_obj, state)
        _start_stream(td_obj, symbols)

        last_watchlist_check = time.monotonic()
        try:
            while True:
                time.sleep(1)
                now = time.monotonic()

                if WATCHLIST_POLL > 0 and not TRUEDATA_SYMBOLS.strip():
                    if now - last_watchlist_check >= WATCHLIST_POLL:
                        last_watchlist_check = now
                        new_symbols = _fetch_watchlist()
                        if new_symbols and set(new_symbols) != set(symbols):
                            print("Watchlist changed. Restarting stream...")
                            _backfill(td_obj, symbols, state.last_seen_by_symbol)
                            _stop_stream(td_obj, symbols)
                            symbols = new_symbols
                            td_obj = _build_td()
                            state = BridgeState()
                            _register_callbacks(td_obj, state)
                            _start_stream(td_obj, symbols)

                if STALE_AFTER > 0 and now - state.last_event >= STALE_AFTER:
                    print("Stream stale. Reconnecting...")
                    _backfill(td_obj, symbols, state.last_seen_by_symbol)
                    _stop_stream(td_obj, symbols)
                    break
        except KeyboardInterrupt:
            print("Stopping TrueData stream...")
            _backfill(td_obj, symbols, state.last_seen_by_symbol)
            _stop_stream(td_obj, symbols)
            sys.exit(0)
        except Exception as exc:
            print(f"Stream error: {exc}")
            _backfill(td_obj, symbols, state.last_seen_by_symbol)
            _stop_stream(td_obj, symbols)

        time.sleep(RECONNECT_BACKOFF)


if __name__ == "__main__":
    main()
