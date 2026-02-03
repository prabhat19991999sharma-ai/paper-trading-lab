import csv
from pathlib import Path
from typing import Iterable, Tuple

from .db import get_connection


ALLOWED_FIELDS = {"ts", "timestamp", "symbol", "open", "high", "low", "close", "volume"}


def normalize_row(row: dict) -> dict:
    lowered = {k.strip().lower(): v for k, v in row.items() if k}
    if "ts" not in lowered and "timestamp" in lowered:
        lowered["ts"] = lowered["timestamp"]
    missing = {"ts", "symbol", "open", "high", "low", "close", "volume"} - set(lowered)
    if missing:
        raise ValueError(f"Missing columns: {', '.join(sorted(missing))}")
    return {
        "ts": lowered["ts"].strip(),
        "symbol": lowered["symbol"].strip().upper(),
        "open": float(lowered["open"]),
        "high": float(lowered["high"]),
        "low": float(lowered["low"]),
        "close": float(lowered["close"]),
        "volume": float(lowered["volume"]),
    }


def load_csv_to_db(file_path: Path) -> Tuple[int, Iterable[str]]:
    rows = []
    symbols = set()
    with file_path.open("r", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("CSV has no header")
        for raw in reader:
            normalized = normalize_row(raw)
            rows.append(normalized)
            symbols.add(normalized["symbol"])

    if not rows:
        return 0, []

    conn = get_connection()
    cur = conn.cursor()
    cur.executemany(
        """
        INSERT OR IGNORE INTO bars (ts, symbol, open, high, low, close, volume)
        VALUES (:ts, :symbol, :open, :high, :low, :close, :volume);
        """,
        rows,
    )
    conn.commit()
    conn.close()
    return len(rows), sorted(symbols)
