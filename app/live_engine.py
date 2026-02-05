from __future__ import annotations

import asyncio
import math
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional

import pytz
from fastapi import WebSocket

from .config import CONFIG
from .db import clear_simulation_data
from .simulator import store_daily_result, store_trade
from .simulator import store_daily_result, store_trade
from .strategy_core import DailyStats, SymbolState, Trade, parse_dt, parse_time
from .safety import SafetyManager, SafetyLimits


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict) -> None:
        dead: List[WebSocket] = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead.append(connection)
        for connection in dead:
            self.disconnect(connection)


class LiveEngine:
    def __init__(self, manager: ConnectionManager, loop: asyncio.AbstractEventLoop) -> None:
        self.manager = manager
        self.loop = loop
        self.running = False
        self.mode = "idle"
        self.speed = 60.0
        self.stop_event = threading.Event()
        self.thread: Optional[threading.Thread] = None
        self.bars: List[dict] = []
        self.bar_index = 0
        self.state_by_symbol: Dict[str, SymbolState] = {}
        self.daily_stats: Dict[str, DailyStats] = {}
        self.last_quotes: Dict[str, float] = {}  # Symbol -> Last Price
        self.equity = CONFIG.initial_capital
        self.lock = threading.Lock()
        
        # Broker initialization
        self.broker = None
        if CONFIG.broker_name == "angel-one":
            from .broker.angel_one import AngelOneBroker
            self.broker = AngelOneBroker(
                CONFIG.angel_api_key, 
                CONFIG.angel_client_id, 
                CONFIG.angel_password,
                CONFIG.angel_totp_key
            )
        elif CONFIG.broker_name == "dhan":
            from .broker.dhan import DhanBroker
            self.broker = DhanBroker(
                CONFIG.dhan_client_id,
                CONFIG.dhan_access_token
            )

        if self.broker:
            # Try connecting in a non-blocking way or log status
            try:
                if self.broker.connect():
                    print(f"Broker ({CONFIG.broker_name}) connected successfully")
                else:
                    print(f"Broker ({CONFIG.broker_name}) connection failed")
            except Exception as e:
                print(f"Broker init error: {e}")

        self.tz = pytz.timezone(CONFIG.timezone)
        self.breakout_time = parse_time(CONFIG.breakout_time)
        self.first_30_start = parse_time(CONFIG.first_30_start)
        self.first_30_end = parse_time(CONFIG.first_30_end)
        
        # Safety Manager Initialization
        self.safety = SafetyManager(
            SafetyLimits(
                max_trades_per_day=CONFIG.max_trades_per_day,
                max_loss_per_day=CONFIG.max_loss_per_day,
                max_position_size=CONFIG.max_position_size,
                max_positions_open=CONFIG.max_positions_open
            ),
            timezone=CONFIG.timezone
        )

    def status(self) -> dict:
        return {
            "running": self.running,
            "mode": self.mode,
            "speed": self.speed,
            "index": self.bar_index,
            "total": len(self.bars),
            "broker_connected": self.broker is not None,
            "broker_name": CONFIG.broker_name,
            "trading_mode": CONFIG.trading_mode,
            "safety_status": self.safety.get_status()
        }

    def start(self, speed: float = 60.0, reset: bool = True) -> dict:
        if self.running:
            return self.status()

        if reset:
            clear_simulation_data()
            self.state_by_symbol.clear()
            self.daily_stats.clear()
            self.last_quotes.clear()
            self.equity = CONFIG.initial_capital
            self.bar_index = 0

        from .simulator import load_bars

        self.bars = load_bars()
        if not self.bars:
            return {"running": False, "error": "No bars available"}

        self.speed = max(speed, 0.1)
        self.stop_event.clear()
        self.running = True
        self.mode = "replay"
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        self._broadcast_status()
        return self.status()


    def stop(self) -> dict:
        if not self.running:
            return self.status()
        self.stop_event.set()
        self.running = False
        self.mode = "idle"
        self._broadcast_status()
        return self.status()

    def process_external_bar(self, bar: dict) -> Optional[dict]:
        if not self.running:
            self.running = True
            self.mode = "stream"
            self._broadcast_status()
        with self.lock:
            event = self._process_bar(bar)
        if event:
            self._broadcast(event)
        self._broadcast(
            {
                "type": "bar",
                "bar": {
                    "ts": bar["ts"],
                    "symbol": bar["symbol"],
                    "open": bar["open"],
                    "high": bar["high"],
                    "low": bar["low"],
                    "close": bar["close"],
                },
                "equity": self.equity,
            }
        )
        return event

    def _broadcast_status(self) -> None:
        self._broadcast({"type": "status", **self.status()})

    def _broadcast(self, payload: dict) -> None:
        if self.loop.is_closed():
            return
        asyncio.run_coroutine_threadsafe(self.manager.broadcast(payload), self.loop)

    def _run_loop(self) -> None:
        while not self.stop_event.is_set() and self.bar_index < len(self.bars):
            bar = self.bars[self.bar_index]
            self.bar_index += 1
            with self.lock:
                event = self._process_bar(bar)

            if event:
                self._broadcast(event)

            self._broadcast(
                {
                    "type": "bar",
                    "bar": {
                        "ts": bar["ts"],
                        "symbol": bar["symbol"],
                        "open": bar["open"],
                        "high": bar["high"],
                        "low": bar["low"],
                        "close": bar["close"],
                    },
                    "equity": self.equity,
                    "index": self.bar_index,
                    "total": len(self.bars),
                }
            )

            sleep_seconds = 60.0 / self.speed
            time.sleep(max(0.01, sleep_seconds))

        self.running = False
        self.mode = "idle"
        self._broadcast({"type": "done", **self.status()})

    def _risk_limited_qty(self, entry_price: float, stop_loss: float) -> int:
        risk_per_share = entry_price - stop_loss
        if risk_per_share <= 0:
            return 0

        qty_by_equity = math.floor((self.equity * CONFIG.max_position_pct) / entry_price)
        if CONFIG.max_risk_pct <= 0:
            return qty_by_equity

        max_risk = self.equity * CONFIG.max_risk_pct
        qty_by_risk = math.floor(max_risk / risk_per_share)
        return max(0, min(qty_by_equity, qty_by_risk))

    def _process_bar(self, bar: dict) -> Optional[dict]:
        symbol = bar["symbol"]
        state = self.state_by_symbol.setdefault(symbol, SymbolState())
        
        # Update last quote
        self.last_quotes[symbol] = float(bar["close"])

        dt = parse_dt(bar["ts"], self.tz)
        local_date = dt.strftime("%Y-%m-%d")
        local_time = dt.time()

        if state.current_day != local_date:
            state.current_day = local_date
            state.high_930 = None
            state.high_30 = None
            state.trades_today = 0
            state.open_trade = None

        stats = self.daily_stats.setdefault(local_date, DailyStats())
        if stats.trades >= CONFIG.max_trades_per_day_global:
            return None
        if stats.realized_pnl <= CONFIG.max_daily_loss:
            return None

        if local_time == self.breakout_time:
            state.high_930 = float(bar["high"])

        if self.first_30_start <= local_time <= self.first_30_end:
            state.high_30 = float(bar["high"]) if state.high_30 is None else max(state.high_30, float(bar["high"]))

        if state.open_trade is None and state.high_930 and state.high_30:
            if state.trades_today < CONFIG.max_trades_per_day_per_symbol and float(bar["close"]) > state.high_930 and float(bar["close"]) > state.high_30:
                # SAFETY CHECK
                allowed, reason = self.safety.is_trading_allowed()
                if not allowed:
                    print(f"Trade blocked by safety: {reason}")
                    return None

                entry_price = float(bar["close"])
                stop_loss = float(bar["low"])
                qty = self._risk_limited_qty(entry_price, stop_loss)
                
                # Position Size Check
                if qty > 0:
                    position_value = qty * entry_price
                    size_ok, size_reason = self.safety.validate_position_size(position_value)
                    if not size_ok:
                        print(f"Trade blocked: {size_reason}")
                        qty = 0  # Cancel trade
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
                    
                    # Record usage in safety manager
                    self.safety.record_position_open()

                    # --- LIVE TRADING EXECUTION (ENTRY) ---
                    if CONFIG.trading_mode == "LIVE":
                        if self.broker:
                            try:
                                # Place Market Order for immediate entry
                                resp = self.broker.place_order(
                                    symbol=symbol,
                                    side="BUY",
                                    qty=qty,
                                    price=0.0,  # Market order
                                    stop_loss=stop_loss,
                                    tag="algo-entry"
                                )
                                print(f"[REAL TRADE] Entry {symbol}: {resp}")
                                if resp.status == "failed":
                                    # If broker fails, we should probably cancel the internal trade too
                                    # But for now we just log error
                                    pass
                            except Exception as e:
                                print(f"[REAL TRADE ERROR] Entry {symbol}: {e}")
                        else:
                             print("LIVE mode enabled but broker not connected!")
                    else:
                        print(f"[PAPER TRADE] Entry {symbol} Qty {qty} @ {entry_price}")

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
                
                # --- LIVE TRADING EXECUTION (EXIT) ---
                if CONFIG.trading_mode == "LIVE":
                    if self.broker:
                        try:
                            # Place Market Order for exit
                            resp = self.broker.place_order(
                                symbol=symbol,
                                side="SELL",
                                qty=state.open_trade.qty,
                                price=0.0,
                                tag="algo-exit"
                            )
                            print(f"[REAL TRADE] Exit {symbol}: {resp}")
                        except Exception as e:
                            print(f"[REAL TRADE ERROR] Exit {symbol}: {e}")
                else:
                    print(f"[PAPER TRADE] Exit {symbol} PnL {state.open_trade.pnl:.2f}")

                # Update safety stats
                self.safety.record_trade(state.open_trade.pnl)
                self.safety.record_position_close()

                store_trade(state.open_trade)

                stats.trades += 1
                stats.realized_pnl += state.open_trade.pnl
                stats.r_total += state.open_trade.r_multiple
                self.equity += state.open_trade.pnl

                if state.open_trade.pnl >= 0:
                    stats.wins += 1
                else:
                    stats.losses += 1

                store_daily_result(local_date, stats)
                trade_payload = {
                    "type": "trade",
                    "trade": {
                        "symbol": state.open_trade.symbol,
                        "side": state.open_trade.side,
                        "qty": state.open_trade.qty,
                        "entry_time": state.open_trade.entry_time,
                        "entry_price": state.open_trade.entry_price,
                        "exit_time": state.open_trade.exit_time,
                        "exit_price": state.open_trade.exit_price,
                        "pnl": state.open_trade.pnl,
                        "r_multiple": state.open_trade.r_multiple,
                    },
                    "summary": {
                        "date": local_date,
                        "trades": stats.trades,
                        "wins": stats.wins,
                        "losses": stats.losses,
                        "win_rate": stats.win_rate,
                        "realized_pnl": stats.realized_pnl,
                        "avg_r": stats.avg_r,
                    },
                    "broker_order": "sent" if self.broker else "paper"
                }
                state.open_trade = None
                return trade_payload

        return None
