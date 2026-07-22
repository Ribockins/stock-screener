"""SVI — instrument response priors (seed → ledger stats later)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IRP_PATH = ROOT / "config" / "irp_seed.json"


def svi_weight(instrument_name: str) -> int:
    if not IRP_PATH.exists():
        return 0
    data = json.loads(IRP_PATH.read_text(encoding="utf-8"))
    row = data.get("by_instrument", {}).get(instrument_name, {})
    return int(row.get("svi", 0))
