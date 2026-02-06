from __future__ import annotations

import asyncio
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

import pytz
from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import CONFIG
from .data_loader import load_csv_to_db
from .db import clear_bars, clear_simulation_data, get_connection, init_db
from .ingest import Bar, BarAggregator, insert_bar
from .live_engine import ConnectionManager, LiveEngine
from .dhan_marketfeed import DhanMarketFeed
from .simulator import simulate
from .watchlist import ensure_watchlist, load_watchlist, save_watchlist

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
DATA_DIR = BASE_DIR / "data"

app = FastAPI(title="Paper Trading Lab")


class TickIn(BaseModel):
    ts: str
    symbol: str
    price: float
    volume: float = 0.0


class BarIn(BaseModel):
    ts: str
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float =0.0


class WatchlistIn(BaseModel):
    symbols: Union[list[str], str]


class TradingModeIn(BaseModel):
    mode: str
    confirm: bool = False


@app.on_event("startup")
async def on_startup() -> None:
    init_db()
    _auto_load_sample_data_if_empty()
    app.state.manager = ConnectionManager()
    app.state.loop = asyncio.get_running_loop()
    app.state.live_engine = LiveEngine(app.state.manager, app.state.loop)
    app.state.aggregator = BarAggregator(pytz.timezone(CONFIG.timezone))
    ensure_watchlist([
        "ASHOKLEY",
        "AXISBANK",
        "BANKBARODA",
        "BHARTIARTL",
        "DELHIVERY",
        "HDFCBANK",
        "HINDALCO",
        "HINDUNILVR",
        "ICICIBANK",
        "INFY",
        "IRCTC",
        "ITC",
        "KOTAKBANK",
        "LICHSGFIN",
        "NMDCSTEEL",
        "OBEROIRLTY",
        "ONGC",
        "RBLBANK",
        "RELIANCE",
        "SBIN",
        "SHRIRAMFIN",
        "TCS",
        "TORNTPOWER",
        "UJJIVANSFB",
        "VOLTAS"
    ])

    # Start Dhan tick feed (for real-time quotes) if configured
    if (
        CONFIG.broker_name == "dhan"
        and CONFIG.dhan_client_id
        and CONFIG.dhan_access_token
        and CONFIG.dhan_feed_enabled
    ):
        symbols = load_watchlist()

        def on_tick(symbol: str, price: float, ts: str, volume: float) -> None:
            bar = app.state.aggregator.ingest_tick(
                ts=ts,
                symbol=symbol.upper(),
                price=price,
                volume=volume,
            )
            app.state.live_engine.update_quote(symbol.upper(), price, ts)
            if bar:
                insert_bar(bar)
                app.state.live_engine.process_external_bar(asdict(bar))

        app.state.market_feed = DhanMarketFeed(
            client_id=CONFIG.dhan_client_id,
            access_token=CONFIG.dhan_access_token,
            security_map=app.state.live_engine.broker.security_map if app.state.live_engine.broker else {},
            on_tick=on_tick,
            timezone=CONFIG.timezone,
            version=CONFIG.dhan_feed_version,
        )
        app.state.market_feed.start(symbols)
    else:
        app.state.market_feed = None


@app.on_event("shutdown")
async def on_shutdown() -> None:
    market_feed = getattr(app.state, "market_feed", None)
    if market_feed:
        market_feed.stop()


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/debug", response_class=HTMLResponse)
def debug_page() -> str:
    return (STATIC_DIR / "debug.html").read_text(encoding="utf-8")


@app.get("/health")
def health_check() -> JSONResponse:
    return JSONResponse({"status": "ok", "timestamp": str(datetime.now())})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    manager: ConnectionManager = app.state.manager
    await manager.connect(websocket)
    try:
        await websocket.send_json({"type": "status", **app.state.live_engine.status()})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/api/status")
def status() -> JSONResponse:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS count FROM bars;")
    bars = cur.fetchone()["count"]
    cur.execute("SELECT COUNT(*) AS count FROM trades;")
    trades = cur.fetchone()["count"]
    cur.execute("SELECT date FROM daily_results ORDER BY date DESC LIMIT 1;")
    row = cur.fetchone()
    last_date = row["date"] if row else None
    cur.execute("SELECT finished_at FROM runs ORDER BY id DESC LIMIT 1;")
    run_row = cur.fetchone()
    last_run = run_row["finished_at"] if run_row else None
    conn.close()
    return JSONResponse(
        {
            "bars": bars,
            "trades": trades,
            "last_date": last_date,
            "last_run": last_run,
            "timezone": CONFIG.timezone,
        }
    )


@app.get("/api/market/quotes")
def market_quotes() -> JSONResponse:
    return JSONResponse(app.state.live_engine.last_quotes)


@app.get("/api/live/status")
def live_status() -> JSONResponse:
    payload = app.state.live_engine.status()
    market_feed = getattr(app.state, "market_feed", None)
    if market_feed:
        payload["market_feed"] = market_feed.get_status()
    else:
        payload["market_feed"] = {"running": False, "connected": False, "status_message": "disabled"}
    return JSONResponse(payload)


@app.post("/api/live/start")
def live_start(speed: float = 60.0, reset: bool = True) -> JSONResponse:
    result = app.state.live_engine.start(speed=speed, reset=reset)
    return JSONResponse(result)


@app.post("/api/live/stop")
def live_stop() -> JSONResponse:
    result = app.state.live_engine.stop()
    return JSONResponse(result)


# --- TRADING CONTROLS ---

@app.post("/api/trading/mode")
def set_trading_mode(payload: TradingModeIn) -> JSONResponse:
    mode = payload.mode.upper()
    if mode not in ["PAPER", "LIVE"]:
        return JSONResponse({"success": False, "message": "Invalid mode. Use PAPER or LIVE."})
    
    if mode == "LIVE" and not payload.confirm:
        return JSONResponse({"success": False, "message": "Confirmation required for LIVE mode."})
    
    # Update global config
    CONFIG.trading_mode = mode
    
    # Reset safety counters if switching to live
    if mode == "LIVE":
        app.state.live_engine.safety.reset_daily_counters()
        
    return JSONResponse({"success": True, "mode": mode})


@app.get("/api/trading/limits")
def get_trading_limits() -> JSONResponse:
    if not hasattr(app.state, "live_engine"):
         return JSONResponse({})
    return JSONResponse(app.state.live_engine.safety.get_status())


@app.post("/api/trading/killswitch")
def activate_killswitch() -> JSONResponse:
    if hasattr(app.state, "live_engine"):
        app.state.live_engine.safety.activate_kill_switch()
        # Also stop the engine loop if running
        # app.state.live_engine.stop() 
        return JSONResponse({"success": True, "message": "Kill switch activated"})
    return JSONResponse({"success": False, "message": "Engine not initialized"})


@app.get("/api/orders/live")
def get_live_orders() -> JSONResponse:
    """Proxy to get real orders from broker in LIVE mode"""
    # For PAPER mode, we could return simulated trades, but the UI has a separate recent orders table.
    # This endpoint is specifically for the 'Real Broker Orders' if we want to show them.
    # However, the current UI merges them. Let's return broker orders.
    
    engine = app.state.live_engine
    if engine and engine.broker:
        orders = engine.broker.get_orders()
        # Normalize format if needed, but for now passing through
        # Dhan returns list of dicts
        return JSONResponse({"orders": orders})
    
    # If paper mode or no broker, return internal simulated trades for today
    # mapped to similar structure
    return JSONResponse({"orders": []})


@app.get("/api/positions/live")
def get_live_positions() -> JSONResponse:
    """Get live positions from broker"""
    engine = app.state.live_engine
    
    if CONFIG.trading_mode == "LIVE" and engine and engine.broker:
        positions = engine.broker.get_positions()
        return JSONResponse({"positions": positions})
        
    # In Paper Mode, we can return the internal active trade state
    if engine:
        positions = []
        for symbol, state in engine.state_by_symbol.items():
            if state.open_trade:
                t = state.open_trade
                current_price = engine.last_quotes.get(symbol, t.entry_price)
                pnl = (current_price - t.entry_price) * t.qty
                positions.append({
                    "symbol": symbol,
                    "quantity": t.qty,
                    "avg_price": t.entry_price,
                    "pnl": pnl,
                    "ltp": current_price
                })
        return JSONResponse({"positions": positions})
        
    return JSONResponse({"positions": []})


@app.post("/api/ingest/tick")
def ingest_tick(tick: TickIn) -> JSONResponse:
    bar = app.state.aggregator.ingest_tick(
        ts=tick.ts,
        symbol=tick.symbol.upper(),
        price=tick.price,
        volume=tick.volume,
    )
    if bar:
        insert_bar(bar)
        app.state.live_engine.process_external_bar(asdict(bar))
    return JSONResponse({"ok": True, "bar_closed": bar is not None})


@app.post("/api/ingest/bar")
def ingest_bar(bar: BarIn) -> JSONResponse:
    bar_obj = Bar(
        ts=bar.ts,
        symbol=bar.symbol.upper(),
        open=bar.open,
        high=bar.high,
        low=bar.low,
        close=bar.close,
        volume=bar.volume,
    )
    insert_bar(bar_obj)
    app.state.live_engine.process_external_bar(asdict(bar_obj))
    return JSONResponse({"ok": True})


@app.post("/api/ingest/flush")
def ingest_flush() -> JSONResponse:
    flushed = app.state.aggregator.flush()
    count = 0
    for bar in flushed.values():
        insert_bar(bar)
        app.state.live_engine.process_external_bar(asdict(bar))
        count += 1
    return JSONResponse({"flushed": count})


@app.get("/api/watchlist")
def get_watchlist() -> JSONResponse:
    return JSONResponse({"symbols": load_watchlist()})


@app.post("/api/watchlist")
def set_watchlist(payload: WatchlistIn) -> JSONResponse:
    symbols = payload.symbols
    if isinstance(symbols, str):
        symbols = [s.strip() for s in symbols.split(",") if s.strip()]
    saved = save_watchlist(list(symbols))
    market_feed = getattr(app.state, "market_feed", None)
    if market_feed:
        market_feed.update_symbols(saved)
    return JSONResponse({"symbols": saved})


@app.get("/api/dates")
def dates() -> JSONResponse:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT DISTINCT substr(ts, 1, 10) AS date
        FROM bars
        ORDER BY date DESC;
        """
    )
    rows = [row["date"] for row in cur.fetchall()]
    conn.close()
    return JSONResponse({"dates": rows})


@app.get("/api/summary")
def summary(date: Optional[str] = None) -> JSONResponse:
    conn = get_connection()
    cur = conn.cursor()
    if date:
        cur.execute("SELECT * FROM daily_results WHERE date = ?;", (date,))
    else:
        cur.execute("SELECT * FROM daily_results ORDER BY date DESC LIMIT 1;")
    row = cur.fetchone()
    conn.close()
    if not row:
        return JSONResponse({"date": date, "trades": 0, "wins": 0, "losses": 0, "win_rate": 0, "realized_pnl": 0, "avg_r": 0})
    if not row:
        return JSONResponse({"date": date, "trades": 0, "wins": 0, "losses": 0, "win_rate": 0, "realized_pnl": 0, "avg_r": 0})
    return JSONResponse(dict(row))


@app.get("/api/funds")
def get_funds() -> JSONResponse:
    """Get available funds"""
    engine = app.state.live_engine
    
    # If using real broker and LIVE mode (or just to check funds), try broker
    if engine and engine.broker:
        funds = engine.broker.get_funds()
        return JSONResponse({"available_balance": funds})
        
    # Fallback to simulated equity
    return JSONResponse({"available_balance": engine.equity if engine else CONFIG.initial_capital})


@app.get("/api/debug/feed")
def debug_feed_status() -> JSONResponse:
    market_feed = getattr(app.state, "market_feed", None)
    market_info = _market_status()
    if not market_feed:
        payload = {
            "enabled": False,
            "enabled_by_env": CONFIG.dhan_feed_enabled,
            "configured": bool(CONFIG.dhan_client_id and CONFIG.dhan_access_token),
            "status_message": "disabled",
        }
        payload.update(market_info)
        return JSONResponse(payload)
    data = market_feed.get_status()
    data["enabled"] = True
    data["enabled_by_env"] = CONFIG.dhan_feed_enabled
    data["configured"] = bool(CONFIG.dhan_client_id and CONFIG.dhan_access_token)
    data.update(market_info)
    return JSONResponse(data)


@app.post("/api/feed/start")
def start_feed() -> JSONResponse:
    if not (CONFIG.dhan_client_id and CONFIG.dhan_access_token):
        return JSONResponse({"success": False, "message": "Dhan credentials missing"})

    market_feed = getattr(app.state, "market_feed", None)
    if market_feed and market_feed.running:
        return JSONResponse({"success": True, "message": "already running", "status": market_feed.get_status()})

    if not market_feed:
        def on_tick(symbol: str, price: float, ts: str, volume: float) -> None:
            bar = app.state.aggregator.ingest_tick(
                ts=ts,
                symbol=symbol.upper(),
                price=price,
                volume=volume,
            )
            app.state.live_engine.update_quote(symbol.upper(), price, ts)
            if bar:
                insert_bar(bar)
                app.state.live_engine.process_external_bar(asdict(bar))

        market_feed = DhanMarketFeed(
            client_id=CONFIG.dhan_client_id,
            access_token=CONFIG.dhan_access_token,
            security_map=app.state.live_engine.broker.security_map if app.state.live_engine.broker else {},
            on_tick=on_tick,
            timezone=CONFIG.timezone,
            version=CONFIG.dhan_feed_version,
        )
        app.state.market_feed = market_feed

    market_feed.start(load_watchlist())
    return JSONResponse({"success": True, "message": "started", "status": market_feed.get_status()})


@app.post("/api/feed/stop")
def stop_feed() -> JSONResponse:
    market_feed = getattr(app.state, "market_feed", None)
    if not market_feed:
        return JSONResponse({"success": True, "message": "already stopped"})
    market_feed.stop()
    return JSONResponse({"success": True, "message": "stopped", "status": market_feed.get_status()})


@app.get("/api/trades")
def trades(date: Optional[str] = None) -> JSONResponse:
    conn = get_connection()
    cur = conn.cursor()
    if date:
        cur.execute(
            """
            SELECT * FROM trades
            WHERE substr(entry_time, 1, 10) = ?
            ORDER BY entry_time ASC;
            """,
            (date,),
        )
    else:
        cur.execute(
            """
            SELECT * FROM trades
            ORDER BY entry_time DESC
            LIMIT 100;
            """
        )
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return JSONResponse({"trades": rows})


@app.get("/api/equity")
def equity(date: Optional[str] = None) -> JSONResponse:
    conn = get_connection()
    cur = conn.cursor()
    if date:
        cur.execute(
            """
            SELECT exit_time, pnl
            FROM trades
            WHERE substr(exit_time, 1, 10) = ?
            ORDER BY exit_time ASC;
            """,
            (date,),
        )
    else:
        cur.execute("SELECT exit_time, pnl FROM trades ORDER BY exit_time ASC;")
    rows = cur.fetchall()
    conn.close()

    equity = CONFIG.initial_capital
    points = []
    for row in rows:
        equity += row["pnl"]
        points.append({"time": row["exit_time"], "equity": equity})
    return JSONResponse({"points": points})


@app.post("/api/simulate")
def run_simulation() -> JSONResponse:
    result = simulate()
    return JSONResponse({"result": result})


@app.post("/api/data/upload")
def upload_data(file: UploadFile = File(...)) -> JSONResponse:
    if not file.filename:
        return JSONResponse({"error": "No file uploaded"}, status_code=400)

    contents = file.file.read()
    tmp_path = DATA_DIR / f"upload_{datetime.utcnow().timestamp()}.csv"
    tmp_path.write_bytes(contents)

    try:
        count, symbols = load_csv_to_db(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    return JSONResponse({"inserted": count, "symbols": symbols})


@app.post("/api/data/reset")
def reset_data() -> JSONResponse:
    clear_bars()
    clear_simulation_data()
    _auto_load_sample_data_if_empty()
    return JSONResponse({"ok": True})


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _auto_load_sample_data_if_empty() -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS count FROM bars;")
    count = cur.fetchone()["count"]
    conn.close()
    if count == 0:
        sample = DATA_DIR / "sample_bars.csv"
        if sample.exists():
            load_csv_to_db(sample)


def _market_status() -> dict:
    tz = pytz.timezone(CONFIG.timezone)
    now = datetime.now(tz)
    # NSE normal session: 09:15 - 15:30 IST, weekdays only.
    open_time = now.replace(hour=9, minute=15, second=0, microsecond=0)
    close_time = now.replace(hour=15, minute=30, second=0, microsecond=0)
    is_weekday = now.weekday() < 5
    is_open = is_weekday and open_time <= now <= close_time
    return {
        "market_open": is_open,
        "market_status": "open" if is_open else "closed",
        "market_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "market_timezone": CONFIG.timezone,
        "market_session": "09:15-15:30",
    }
