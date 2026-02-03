import json
from pathlib import Path
from typing import List

BASE_DIR = Path(__file__).resolve().parent.parent
WATCHLIST_PATH = BASE_DIR / "data" / "watchlist.json"


def load_watchlist() -> List[str]:
    if not WATCHLIST_PATH.exists():
        return []
    try:
        data = json.loads(WATCHLIST_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    symbols = data.get("symbols", []) if isinstance(data, dict) else []
    return [str(s).upper() for s in symbols if str(s).strip()]


def save_watchlist(symbols: List[str]) -> List[str]:
    cleaned = sorted({str(s).upper().strip() for s in symbols if str(s).strip()})
    WATCHLIST_PATH.write_text(json.dumps({"symbols": cleaned}, indent=2), encoding="utf-8")
    return cleaned


def ensure_watchlist(default_symbols: List[str]) -> List[str]:
    if WATCHLIST_PATH.exists():
        return load_watchlist()
    return save_watchlist(default_symbols)
