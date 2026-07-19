"""Standard scan timeframes for GEM multi-timeframe analysis."""

from typing import Dict, List, Tuple

# interval_key -> (label, yfinance interval hint for docs)
SCAN_TIMEFRAMES: List[Tuple[str, str]] = [
    ("15", "15m"),
    ("60", "1h"),
    ("240", "4h"),
    ("1d", "1d"),
]

DEFAULT_TIMEFRAMES = [k for k, _ in SCAN_TIMEFRAMES]

# Bar interval in seconds (for GEM 1.5 R-cycle window)
TF_INTERVAL_SECONDS: Dict[str, int] = {
    "15": 900,
    "60": 3600,
    "240": 14400,
    "1d": 86400,
}

TF_LABELS: Dict[str, str] = {k: label for k, label in SCAN_TIMEFRAMES}

TF_SHORT: Dict[str, str] = {
    "15": "M15",
    "60": "H1",
    "240": "H4",
    "1d": "D1",
}
