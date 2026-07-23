#!/usr/bin/env python3
"""
Morning Command Center — one table: TIME profile + EDGE/SVI priors + GEM readiness slots.

Usage:
  python scripts/morning_command_center.py
  python scripts/morning_command_center.py --now "2026-07-23 14:35" --tz America/New_York

Outputs: reports/morning_command_center.md
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ROOT / "config" / "temporal_profiles"
IRP = ROOT / "config" / "irp_seed.json"
OUT = ROOT / "reports" / "morning_command_center.md"

WD_MAP = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}


def parse_hm(s: str) -> tuple[int, int]:
    h, m = s.split(":")
    return int(h), int(m)


def in_window(now: datetime, start: str, end: str) -> bool:
    sh, sm = parse_hm(start)
    eh, em = parse_hm(end)
    t = now.hour * 60 + now.minute
    a = sh * 60 + sm
    b = eh * 60 + em
    if a <= b:
        return a <= t <= b
    return t >= a or t <= b


def load_profiles() -> list[dict]:
    rows = []
    for p in sorted(PROFILES.glob("*.json")):
        if p.name == "schema.json":
            continue
        rows.append(json.loads(p.read_text(encoding="utf-8")))
    return rows


def svi(symbol: str) -> int:
    if not IRP.exists():
        return 0
    data = json.loads(IRP.read_text(encoding="utf-8"))
    by = data.get("by_instrument", {})
    aliases = {
        "NGAS": "NG",
        "SPX500": "US500",
        "USOil": "WTI",
        "UKOil": "Brent",
    }
    key = aliases.get(symbol, symbol)
    return int(by.get(key, {}).get("svi", 0))


def gem_slot(symbol: str) -> str:
    """Placeholder until live scan wired; document required checks."""
    return "RSI+Div+Candle · Score · Exec WAIT/WARN/OK"


def vector_slot(symbol: str, window: dict) -> str:
    return f"HOLD until {window.get('exit_et', '?')} · FAST exit on SL"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--now", type=str, default=None, help="ISO local time in --tz")
    parser.add_argument("--tz", type=str, default="America/New_York")
    args = parser.parse_args()
    tz = ZoneInfo(args.tz)
    now = datetime.now(tz) if not args.now else datetime.fromisoformat(args.now).replace(tzinfo=tz)
    wday = WD_MAP[now.weekday()]

    lines = [
        "# Morning Command Center",
        "",
        f"_Generated {now.isoformat()} · weekday **{wday}** · TZ **{args.tz}**_",
        "",
        "## Active time windows (TEMPORAL)",
        "",
        "| Symbol | Window | Phase | Entry | Exit | TP | Side | Conf | SVI | GEM | VECTOR |",
        "|--------|--------|-------|-------|------|-----|------|------|-----|-----|--------|",
    ]

    active_any = False
    for prof in load_profiles():
        sym = prof["symbol"]
        for w in prof.get("windows", []):
            days = w.get("weekdays") or ["Mon", "Tue", "Wed", "Thu", "Fri"]
            if wday not in days:
                continue
            start = w.get("start_et", "00:00")
            entry = w.get("entry_et", start)
            exit_ = w.get("exit_et", "23:59")
            # Active from start through exit
            if not in_window(now, start, exit_):
                continue
            active_any = True
            phase = "PRE-ENTRY" if in_window(now, start, entry) else "IN-TRADE"
            tp = w.get("tp_points", "")
            if w.get("tp_mode") == "min_of_both":
                tp = f"min({w.get('tp_points')}, {int((w.get('tp_pct_impulse') or 0.5)*100)}%imp)"
            conf = w.get("confidence", "")
            lines.append(
                f"| **{sym}** | {w.get('id')} | {phase} | {entry} | {exit_} | {tp} | {w.get('side')} | {conf} | {svi(sym):+d} | {gem_slot(sym)} | {vector_slot(sym, w)} |"
            )

    if not active_any:
        lines.append("| _—_ | _No profile window active now_ | | | | | | | | | |")

    lines.extend(
        [
            "",
            "## Today’s full schedule (all symbols)",
            "",
            "| Symbol | ID | Start | Entry | Exit | Weekdays | Notes |",
            "|--------|-----|-------|-------|------|----------|-------|",
        ]
    )
    for prof in load_profiles():
        sym = prof["symbol"]
        for w in prof.get("windows", []):
            days = ",".join(w.get("weekdays", []))
            if wday not in (w.get("weekdays") or []):
                continue
            lines.append(
                f"| {sym} | {w.get('id')} | {w.get('start_et')} | {w.get('entry_et')} | {w.get('exit_et')} | {days} | {w.get('label', '')} |"
            )

    lines.extend(
        [
            "",
            "## Stack checklist (one glance)",
            "",
            "1. **TEMPORAL** — row active above? impulse ≥ min?",
            "2. **EDGE heat** — combo / EDGE+ hot on that symbol (run GEM My List scan).",
            "3. **GEM** — WAIT → WARNING → CONFIRMED (`execution_tier`).",
            "4. **VECTOR** — hold to `exit_et` unless SL or GEM exit flip.",
            "5. **APEX** — pairs only when spread z extreme (US30/US500, UK/CAC).",
            "",
            "See `docs/platform_master_playbook.md`.",
        ]
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
