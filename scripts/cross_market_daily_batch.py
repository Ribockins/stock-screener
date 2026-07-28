#!/usr/bin/env python3
"""Daily Sierra batch — aligned calendar correlations, lead-lag, weekday bias (2014–2026)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

UPLOADS = Path("/home/ubuntu/.cursor/projects/workspace/uploads")
OUT_JSON = Path("/workspace/reports/cross_market_daily.json")
OUT_MD = Path("/workspace/docs/cross_market_daily_report.md")

DAILY_FILES = [
    ("US30", "US30.dly_BarData_d97c.txt"),
    ("UK100", "UK100.dly_BarData_7e21.txt"),
    ("FRA40", "FRA40.dly_BarData_efa6.txt"),
    ("USOil", "USOil.dly_BarData_0205.txt"),
    ("UKOil", "UKOil.dly_BarData_21d7.txt"),
    ("XAUUSD", "XAUUSD.dly_BarData_5b1c.txt"),
    ("XAGUSD", "XAGUSD.dly_BarData_e3ba.txt"),
    ("NGAS", "1_d_NGAS.dly_BarData_7a65.txt"),
]

WD_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri"]

PAIRS = [
    ("US30", "UK100"),
    ("US30", "FRA40"),
    ("UK100", "FRA40"),
    ("US30", "USOil"),
    ("US30", "XAUUSD"),
    ("USOil", "XAUUSD"),
    ("USOil", "UKOil"),
    ("XAUUSD", "XAGUSD"),
    ("US30", "NGAS"),
    ("USOil", "NGAS"),
]


def load_daily(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path)
    raw.columns = [c.strip() for c in raw.columns]
    raw["dt"] = pd.to_datetime(raw["Date"].astype(str).str.strip())
    raw = raw.sort_values("dt").reset_index(drop=True)
    for c in ["Open", "High", "Low", "Last"]:
        raw[c.lower()] = raw[c].astype(float)
    raw["vol"] = raw["Volume"].astype(int)
    raw["range"] = raw["high"] - raw["low"]
    raw["ret"] = raw["last"].pct_change()
    # Clip extreme daily moves (e.g. WTI Apr 2020) for weekday / stress stats
    raw["ret_clip"] = raw["ret"].clip(-0.15, 0.15)
    raw["wday"] = raw["dt"].dt.day_name().str[:3]
    return raw


def weekday_profile(df: pd.DataFrame, symbol: str) -> dict:
    w = df[df["wday"].isin(WD_ORDER)].copy()
    g = w.groupby("wday").agg(
        n=("ret_clip", "count"),
        avg_ret=("ret_clip", "mean"),
        avg_range=("range", "mean"),
        pos_pct=("ret", lambda s: (s > 0).mean()),
    )
    rows = {}
    for d in WD_ORDER:
        if d in g.index:
            rows[d] = {
                "avg_ret_pct": round(float(g.loc[d, "avg_ret"]) * 100, 3),
                "avg_range": round(float(g.loc[d, "avg_range"]), 4),
                "pos_pct": round(float(g.loc[d, "pos_pct"]) * 100, 1),
            }
    return {"symbol": symbol, "from": str(df["dt"].iloc[0].date()), "to": str(df["dt"].iloc[-1].date()), "weekdays": rows}


def lead_lag_daily(a: pd.Series, b: pd.Series, max_lag: int = 5) -> dict:
    """Positive lag = A leads B by lag trading days."""
    idx = a.index.intersection(b.index)
    if len(idx) < 100:
        return {"n": len(idx), "best_lag_days": None, "corr": None}
    aa = a.loc[idx].values
    bb = b.loc[idx].values
    best_lag, best_c = 0, -2.0
    for lag in range(-max_lag, max_lag + 1):
        if lag < 0:
            x, y = aa[-lag:], bb[:lag]
        elif lag > 0:
            x, y = aa[:-lag], bb[lag:]
        else:
            x, y = aa, bb
        if len(x) < 50:
            continue
        c = np.corrcoef(x, y)[0, 1]
        if c == c and c > best_c:
            best_c, best_lag = float(c), lag
    return {"n": int(len(idx)), "best_lag_days": best_lag, "corr": round(best_c, 3)}


def stress_follow(
    panel: pd.DataFrame,
    shock: str,
    followers: list[str],
    *,
    direction: str = "down",
    thresh: float = 0.01,
) -> list[dict]:
    """After shock symbol daily move, median follower ret next 1d."""
    r = panel.copy()
    shock_ret = r[shock]
    rows = []
    if direction == "down":
        mask = shock_ret <= -thresh
        label = f"{shock} ≤{-thresh*100:.0f}%"
    else:
        mask = shock_ret >= thresh
        label = f"{shock} ≥{thresh*100:.0f}%"
    dates = shock_ret.index[mask]
    for f in followers:
        if f not in r.columns:
            continue
        nxt = []
        for d in dates:
            loc = r.index.get_loc(d)
            if loc + 1 >= len(r):
                continue
            nxt.append(r.iloc[loc + 1][f])
        if len(nxt) < 20:
            continue
        s = pd.Series(nxt)
        rows.append(
            {
                "after": label,
                "follower": f,
                "horizon": "next_day",
                "n": len(s),
                "median_ret_pct": round(float(s.median()) * 100, 3),
                "pos_pct": round(float((s > 0).mean()) * 100, 1),
            }
        )
    return rows


def main() -> None:
    frames = {}
    profiles = []
    for sym, fname in DAILY_FILES:
        path = UPLOADS / fname
        if not path.exists():
            continue
        df = load_daily(path)
        frames[sym] = df.set_index("dt")["ret"].rename(sym)
        profiles.append(weekday_profile(df, sym))

    panel = pd.DataFrame(frames).dropna(how="all")
    panel252 = panel.tail(252)

    lags = []
    for a, b in PAIRS:
        if a in panel.columns and b in panel.columns:
            full = lead_lag_daily(panel[a].dropna(), panel[b].dropna())
            recent = lead_lag_daily(panel252[a].dropna(), panel252[b].dropna())
            lags.append({"pair": f"{a}→{b}", "sample": "full", **full})
            lags.append({"pair": f"{a}→{b}", "sample": "252d", **recent})

    corr_full = panel.corr().round(3).to_dict()
    corr_252 = panel252.corr().round(3).to_dict()

    stress = stress_follow(panel, "US30", ["XAUUSD", "USOil", "UK100", "NGAS", "FRA40"], direction="down")
    stress_up = stress_follow(panel, "US30", ["XAUUSD", "USOil"], direction="up")

    brent_wti = None
    if "UKOil" in panel.columns and "USOil" in panel.columns:
        brent_wti = {
            "return_corr_full": round(float(panel["UKOil"].corr(panel["USOil"])), 3),
            "return_corr_252d": round(float(panel252["UKOil"].corr(panel252["USOil"])), 3),
        }

    payload = {
        "profiles": profiles,
        "lead_lag": lags,
        "corr_full": corr_full,
        "corr_252d": corr_252,
        "stress_after_us30_down": stress,
        "stress_after_us30_up": stress_up,
        "brent_wti": brent_wti,
        "aligned_days": int(panel.dropna(how="any").shape[0]),
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "# Cross-market daily report (macro layer)",
        "",
        "_Regenerate: `python scripts/cross_market_daily_batch.py`_",
        "",
        f"Aligned trading days (all symbols): **{payload['aligned_days']}** · sample **2014–2026**",
        "",
        "## Instruments loaded",
        "",
        "| Symbol | From | To |",
        "|--------|------|-----|",
    ]
    for p in profiles:
        lines.append(f"| **{p['symbol']}** | {p['from']} | {p['to']} |")

    lines.extend(["", "## Weekday bias (avg daily return %)", ""])
    for p in profiles:
        parts = [f"{d} {p['weekdays'][d]['avg_ret_pct']:+.3f}%" for d in WD_ORDER if d in p["weekdays"]]
        lines.append(f"- **{p['symbol']}:** " + " · ".join(parts))

    lines.extend(["", "## Correlation (252d, daily returns)", ""])
    lines.append("| | US30 | UK100 | FRA40 | USOil | XAUUSD | NGAS |")
    lines.append("|---|:---:|:---:|:---:|:---:|:---:|:---:|")
    for sym in ["US30", "UK100", "FRA40", "USOil", "XAUUSD", "NGAS"]:
        if sym not in corr_252:
            continue
        row = [sym]
        for col in ["US30", "UK100", "FRA40", "USOil", "XAUUSD", "NGAS"]:
            v = corr_252.get(sym, {}).get(col)
            row.append("—" if v is None or (sym == col) else f"{v:.2f}")
        lines.append("| " + " | ".join(row) + " |")

    lines.extend(["", "## Lead–lag (daily returns, full sample)", ""])
    lines.append("| Pair | Lag (days) | Corr | n | Read |")
    lines.append("|------|------------|------|---|------|")
    for L in lags:
        if L["sample"] != "full":
            continue
        lag = L.get("best_lag_days")
        read = "—"
        if lag is not None:
            a, b = L["pair"].split("→")
            if lag > 0:
                read = f"{a} leads {b} ~{lag}d"
            elif lag < 0:
                read = f"{b} leads {a} ~{-lag}d"
            else:
                read = "same day"
        lines.append(f"| {L['pair']} | {lag} | {L.get('corr')} | {L.get('n')} | {read} |")

    lines.extend(["", "## After US30 shock (next-day median return)", ""])
    lines.append("| Condition | Follower | n | Median | Pos% |")
    lines.append("|-----------|----------|---|--------|------|")
    for s in stress + stress_up:
        lines.append(
            f"| {s['after']} | {s['follower']} | {s['n']} | {s['median_ret_pct']:+.3f}% | {s['pos_pct']}% |"
        )

    if brent_wti:
        lines.extend(
            [
                "",
                f"**Brent–WTI:** daily return corr **{brent_wti['return_corr_full']}** (252d: **{brent_wti['return_corr_252d']}**).",
            ]
        )

    lines.extend(
        [
            "",
            "## How this feeds GEM + VECTOR",
            "",
            "1. **Macro filter:** on US30 down days, gold/oil next-day stats above → bias for mean-reversion or continuation per pair.",
            "2. **EU vs US:** UK100/FRA40 lead-lag vs US30 → which index to watch first in London vs NY handoff.",
            "3. **Intraday execution** still from `cross_market_profile_batch.py` (1m/5m); daily layer sets **directional prior** only.",
            "",
            "JSON: `reports/cross_market_daily.json`",
        ]
    )
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT_MD} and {OUT_JSON}")


if __name__ == "__main__":
    main()
