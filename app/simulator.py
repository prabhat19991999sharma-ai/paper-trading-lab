from __future__ import annotations

import math
from datetime import datetime
from typing import Dict, List, Optional

import pytz

from .config import CONFIG
from .db import clear_simulation_data, get_connection
from .strategy_core import DailyStats, SymbolState, Trade, parse_dt, parse_time


def load_bars(symbols: Optional[List[str]] = None) -> List[dict]:
    conn = get_connection()
    cur = conn.cursor()
    if symbols:
        placeholders = ",".join("?" for _ in symbols)
        cur.execute(
            f"SELECT ts, symbol, open, high, low, close, volume FROM bars WHERE symbol IN ({placeholders}) ORDER BY ts ASC;",
            [s.upper() for s in symbols],
        )
    else:
        cur.execute("SELECT ts, symbol, open, high, low, close, volume FROM bars ORDER BY ts ASC;")

    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows


def store_trade(trade: Trade) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO trades (symbol, side, qty, entry_time, entry_price, stop_loss, target, exit_time, exit_price, pnl, r_multiple, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            trade.symbol,
            trade.side,
            trade.qty,
            trade.entry_time,
            trade.entry_price,
            trade.stop_loss,
            trade.target,
            trade.exit_time,
            trade.exit_price,
            trade.pnl,
            trade.r_multiple,
            trade.status,
        ),
    )
    conn.commit()
    conn.close()


def store_daily_result(date_str: str, stats: DailyStats) -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT OR REPLACE INTO daily_results (date, trades, wins, losses, win_rate, realized_pnl, avg_r)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """,
        (
            date_str,
            stats.trades,
            stats.wins,
            stats.losses,
            stats.win_rate,
            stats.realized_pnl,
            stats.avg_r,
        ),
    )
    conn.commit()
    conn.close()


def _risk_limited_qty(entry_price: float, stop_loss: float, equity: float) -> int:
    risk_per_share = entry_price - stop_loss
    if risk_per_share <= 0:
        return 0

    qty_by_equity = math.floor((equity * CONFIG.max_position_pct) / entry_price)
    if CONFIG.max_risk_pct <= 0:
        return qty_by_equity

    max_risk = equity * CONFIG.max_risk_pct
    qty_by_risk = math.floor(max_risk / risk_per_share)
    return max(0, min(qty_by_equity, qty_by_risk))


def simulate(symbols: Optional[List[str]] = None) -> Dict[str, float]:
    clear_simulation_data()

    tz = pytz.timezone(CONFIG.timezone)
    breakout_time = parse_time(CONFIG.breakout_time)
    first_30_start = parse_time(CONFIG.first_30_start)
    first_30_end = parse_time(CONFIG.first_30_end)

    bars = load_bars(symbols)
    if not bars:
        return {"bars": 0, "trades": 0}

    state_by_symbol: Dict[str, SymbolState] = {}
    daily_stats: Dict[str, DailyStats] = {}
    equity = CONFIG.initial_capital

    bars_processed = 0
    trades_generated = 0

    for bar in bars:
        bars_processed += 1
        symbol = bar["symbol"]
        state = state_by_symbol.setdefault(symbol, SymbolState())

        dt = parse_dt(bar["ts"], tz)
        local_date = dt.strftime("%Y-%m-%d")
        local_time = dt.time()

        if state.current_day != local_date:
            state.current_day = local_date
            state.high_930 = None
            state.high_30 = None
            state.trades_today = 0
            state.open_trade = None

        stats = daily_stats.setdefault(local_date, DailyStats())
        if stats.trades >= CONFIG.max_trades_per_day_global:
            continue
        if stats.realized_pnl <= CONFIG.max_daily_loss:
            continue

        if first_30_start <= local_time <= first_30_end:
            state.high_30 = float(bar["high"]) if state.high_30 is None else max(state.high_30, float(bar["high"]))

        if state.open_trade is None and state.high_30 and local_time > breakout_time:
            if state.trades_today < CONFIG.max_trades_per_day_per_symbol and float(bar["close"]) > state.high_30:
                entry_price = float(bar["close"])
                stop_loss = float(bar["low"])
                qty = _risk_limited_qty(entry_price, stop_loss, equity)
                if qty > 0:
                    risk = entry_price - stop_loss
                    target = entry_price + risk * CONFIG.risk_reward
                    state.open_trade = Trade(
                        symbol=symbol,
                        side="LONG",
                        qty=qty,
                        entry_time=dt.isoformat(),
                        entry_price=entry_price,
                        stop_loss=stop_loss,
                        target=target,
                    )
                    state.trades_today += 1

        if state.open_trade is not None:
            low = float(bar["low"])
            high = float(bar["high"])
            stop_hit = low <= state.open_trade.stop_loss
            target_hit = high >= state.open_trade.target

            exit_price = None
            if stop_hit and target_hit:
                exit_price = state.open_trade.stop_loss if CONFIG.stop_fill_priority == "stop" else state.open_trade.target
            elif stop_hit:
                exit_price = state.open_trade.stop_loss
            elif target_hit:
                exit_price = state.open_trade.target

            if exit_price is not None:
                state.open_trade.exit_time = dt.isoformat()
                state.open_trade.exit_price = exit_price
                state.open_trade.pnl = (exit_price - state.open_trade.entry_price) * state.open_trade.qty
                state.open_trade.r_multiple = (exit_price - state.open_trade.entry_price) / (
                    state.open_trade.entry_price - state.open_trade.stop_loss
                )
                state.open_trade.status = "closed"

                store_trade(state.open_trade)
                trades_generated += 1

                stats.trades += 1
                stats.realized_pnl += state.open_trade.pnl
                stats.r_total += state.open_trade.r_multiple
                equity += state.open_trade.pnl

                if state.open_trade.pnl >= 0:
                    stats.wins += 1
                else:
                    stats.losses += 1

                state.open_trade = None

    for date_str, stats in daily_stats.items():
        store_daily_result(date_str, stats)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO runs (started_at, finished_at, bars_processed, trades_generated)
        VALUES (?, ?, ?, ?);
        """,
        (datetime.utcnow().isoformat(), datetime.utcnow().isoformat(), bars_processed, trades_generated),
    )
    conn.commit()
    conn.close()

    return {"bars": bars_processed, "trades": trades_generated}
