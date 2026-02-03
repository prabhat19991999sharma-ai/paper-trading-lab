import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "papertrade.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS bars (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            symbol TEXT NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume REAL NOT NULL
        );
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_bars_symbol_ts ON bars(symbol, ts);")
    try:
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_bars_symbol_ts_unique ON bars(symbol, ts);")
    except sqlite3.IntegrityError:
        pass

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL,
            qty REAL NOT NULL,
            entry_time TEXT NOT NULL,
            entry_price REAL NOT NULL,
            stop_loss REAL NOT NULL,
            target REAL NOT NULL,
            exit_time TEXT,
            exit_price REAL,
            pnl REAL,
            r_multiple REAL,
            status TEXT NOT NULL
        );
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_trades_symbol_entry ON trades(symbol, entry_time);")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_results (
            date TEXT PRIMARY KEY,
            trades INTEGER NOT NULL,
            wins INTEGER NOT NULL,
            losses INTEGER NOT NULL,
            win_rate REAL NOT NULL,
            realized_pnl REAL NOT NULL,
            avg_r REAL NOT NULL
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL,
            finished_at TEXT NOT NULL,
            bars_processed INTEGER NOT NULL,
            trades_generated INTEGER NOT NULL
        );
        """
    )

    conn.commit()
    conn.close()


def clear_simulation_data() -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM trades;")
    cur.execute("DELETE FROM daily_results;")
    cur.execute("DELETE FROM runs;")
    conn.commit()
    conn.close()


def clear_bars() -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM bars;")
    conn.commit()
    conn.close()
