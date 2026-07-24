#!/usr/bin/env python3
"""Analyze ICE 1m Coffee/Cocoa exports — London open fade & lead-lag (see docs/ice_softs_london_study.md)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parents[1]
LON = ZoneInfo("Europe/London")
WD = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri"}


def load_ice(path: Path) -> pd.Series:
    rows: list[tuple[pd.Timestamp, float]] = []
    with path.open() as f:
        f.readline()
        for line in f:
            p = [x.strip() for x in line.strip().split(",")]
            if len(p) < 6:
                continue
            rows.append((pd.Timestamp(f"{p[0]} {p[1]}").tz_localize(LON), float(p[5])))
    s = pd.Series(dict(rows)).sort_index()
    return s[~s.index.duplicated(keep="last")]


def price_at(px: pd.Series, t0: pd.Timestamp, off_min: int) -> float | None:
    t = t0 + pd.Timedelta(minutes=off_min)
    sub = px.loc[t - pd.Timedelta(minutes=2) : t + pd.Timedelta(minutes=2)]
    if sub.empty:
        return None
    return float(sub.iloc[(abs(sub.index - t)).argmin()])


def cocoa_fade_stats(px: pd.Series, imp_min: int = 10, imp_pct: float = 0.10) -> dict:
    wins = ge50 = n = 0
    for day in sorted(set(px.index.date)):
        if pd.Timestamp(day).weekday() > 4:
            continue
        t0 = px[px.index.date == day].index[0]
        p0, p_imp, p45 = price_at(px, t0, 0), price_at(px, t0, imp_min), price_at(px, t0, 45)
        if None in (p0, p_imp, p45):
            continue
        imp = (p_imp / p0 - 1) * 100
        if abs(imp) < imp_pct:
            continue
        n += 1
        sign = 1 if imp > 0 else -1
        m45 = (p45 / p0 - 1) * 100
        if m45 * imp < 0 and min(abs(m45) / abs(imp) * 100, 200) >= 50:
            ge50 += 1
        if (-sign) * (p45 / p_imp - 1) * 100 > 0:
            wins += 1
    return {"sessions": n, "fade_win_pct": wins / n * 100 if n else 0, "retrace_ge50_pct": ge50 / n * 100 if n else 0}


def same_5m_impulse(kc: pd.Series, cc: pd.Series, h_k: int, m_k: int, h_c: int, m_c: int) -> dict:
    same = total = 0
    for day in sorted(set(kc.index.date) & set(cc.index.date)):
        if pd.Timestamp(day).weekday() > 4:
            continue
        d = pd.Timestamp(day)
        tk = pd.Timestamp(year=d.year, month=d.month, day=d.day, hour=h_k, minute=m_k, tzinfo=LON)
        tc = pd.Timestamp(year=d.year, month=d.month, day=d.day, hour=h_c, minute=m_c, tzinfo=LON)
        pk0, pk5 = price_at(kc, tk, 0), price_at(kc, tk, 5)
        pc0, pc5 = price_at(cc, tc, 0), price_at(cc, tc, 5)
        if None in (pk0, pk5, pc0, pc5):
            continue
        dk, dc = pk5 - pk0, pc5 - pc0
        if dk == 0 or dc == 0:
            continue
        total += 1
        if (dk > 0) == (dc > 0):
            same += 1
    return {"pairs": total, "same_direction_pct": same / total * 100 if total else 0}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--coffee", type=Path, required=True)
    parser.add_argument("--cocoa", type=Path, required=True)
    args = parser.parse_args()
    kc, cc = load_ice(args.coffee), load_ice(args.cocoa)
    print("Coffee bars:", len(kc), kc.index.min(), "->", kc.index.max())
    print("Cocoa  bars:", len(cc), cc.index.min(), "->", cc.index.max())
    print("\n--- Cocoa fade (10m impulse, exit +45m) ---")
    print(cocoa_fade_stats(cc))
    print("\n--- Same 5m impulse 08:15/08:45 (file clock) ---")
    print(same_5m_impulse(kc, cc, 8, 15, 8, 45))
    print("\n--- Same 5m impulse 09:15/09:45 (file clock) ---")
    print(same_5m_impulse(kc, cc, 9, 15, 9, 45))
    return 0


if __name__ == "__main__":
    sys.exit(main())
