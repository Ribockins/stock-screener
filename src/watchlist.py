"""Watchlist load/save for user-selected instruments."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

DEFAULT_WATCHLIST = {
    "refresh_minutes": 5,
    "timeframe": "60",
    "bars": 120,
    "instruments": [
        {"symbol": "AAPL", "exchange": "NASDAQ", "name": "Apple"},
        {"symbol": "MSFT", "exchange": "NASDAQ", "name": "Microsoft"},
        {"symbol": "GOOGL", "exchange": "NASDAQ", "name": "Alphabet"},
        {"symbol": "TSLA", "exchange": "NASDAQ", "name": "Tesla"},
    ],
}


def watchlist_path() -> Path:
    return Path(__file__).resolve().parent.parent / "config" / "watchlist.json"


def load_watchlist(path: Path = None) -> Dict[str, Any]:
    path = path or watchlist_path()
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        save_watchlist(DEFAULT_WATCHLIST, path)
        return DEFAULT_WATCHLIST.copy()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "instruments" not in data:
            data["instruments"] = DEFAULT_WATCHLIST["instruments"]
        return data
    except Exception as e:
        logger.error("Failed to load watchlist: %s", e)
        return DEFAULT_WATCHLIST.copy()


def save_watchlist(data: Dict[str, Any], path: Path = None) -> None:
    path = path or watchlist_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def symbols_from_watchlist(data: Dict[str, Any]) -> List[str]:
    return [i["symbol"] for i in data.get("instruments", []) if i.get("symbol")]
