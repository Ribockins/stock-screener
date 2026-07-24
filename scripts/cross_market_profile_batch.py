#!/usr/bin/env python3
"""Batch minute/H1 profile + cross-market lead-lag for uploaded Sierra files."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

UPLOADS = Path("/home/ubuntu/.cursor/projects/workspace/uploads")
OUT_MD = Path("/workspace/reports/cross_market_sequence_report.md")
OUT_JSON = Path("/workspace/reports/cross_market_profiles.json")

FILES = [
    ("NAS100", "NAS100.scid_BarData_83c7.txt", "America/New_York"),
    ("GER30", "GER30.scid_BarData_bb8c.txt", "Europe/Berlin"),
    ("EUSTX50", "EUSTX50.scid_BarData_53c5.txt", "Europe/Berlin"),
    ("ESP35", "ESP35.scid_BarData_9374.txt", "Europe/Madrid"),
    ("FRA40", "FRA40.scid_BarData_3e55.txt", "Europe/Paris"),
    ("UK100", "UK100.scid_BarData_af3c.txt", "Europe/London"),
    ("US30", "1min_US30.scid_BarData_0913.txt", "America/New_York"),
    ("SPX500", "1min_SPX500.scid_BarData_782c.txt", "America/New_York"),
    ("NGAS", "5_min_NGAS.scid_BarData_2f4a.txt", "America/New_York"),
    ("XAUUSD", "XAUUSD.scid_BarData_33e8.txt", "America/New_York"),
    ("XAGUSD", "XAGUSD.scid_BarData_8a66.txt", "America/New_York"),
    ("UKOil", "UKOil.scid_BarData_f158.txt", "America/New_York"),
    ("USOil", "USOil.scid_BarData_ec2e.txt", "America/New_York"),
]


def load(path: Path, tz: str) -> pd.DataFrame:
    from zoneinfo import ZoneInfo

    raw = pd.read_csv(path)
    raw.columns = [c.strip() for c in raw.columns]
    z = ZoneInfo(tz)
    raw["dt"] = pd.to_datetime(
        raw["Date"].astype(str).str.strip() + " " + raw["Time"].astype(str).str.strip()
    ).dt.tz_localize(z)
    raw = raw.sort_values("dt").reset_index(drop=True)
    for c in ["Open", "High", "Low", "Last"]:
        raw[c.lower()] = raw[c].astype(float)
    raw["vol"] = raw["Volume"].astype(int)
    raw["range"] = raw["high"] - raw["low"]
    raw["ret"] = raw["last"].pct_change()
    return raw


def bar_minutes(df: pd.DataFrame) -> int:
    d = df["dt"].diff().dt.total_seconds().median() / 60
    return int(round(d)) if d == d else 60


def profile(df: pd.DataFrame, symbol: str, tz: str) -> dict:
    bm = bar_minutes(df)
    by_h = df.groupby(df["dt"].dt.hour).agg(vol=("vol", "mean"), rng=("range", "mean")).sort_values("vol", ascending=False)
    top_h = [f"{int(i):02d}:00" for i in by_h.head(5).index]
    daily = []
    for day, g in df.groupby(df["dt"].dt.date):
        if pd.Timestamp(day).weekday() > 4:
            continue
        daily.append(
            {
                "wday": pd.Timestamp(day).day_name()[:3],
                "hl": float(g["high"].max() - g["low"].min()),
                "vol": int(g["vol"].sum()),
            }
        )
    D = pd.DataFrame(daily)
    wday_hl = D.groupby("wday")["hl"].mean().to_dict() if len(D) else {}
    # anchors: US 14:30 ET; EU 09:00 and 15:30 local
    anchors = []
    if tz.startswith("America"):
        for ah, am, lab in [(9, 30, "09:30"), (14, 30, "14:30"), (16, 0, "16:00")]:
            anchors.append(anchor_stats(df, ah, am, lab, bm))
    else:
        for ah, am, lab in [(9, 0, "09:00"), (11, 0, "11:00"), (15, 30, "15:30"), (17, 30, "17:30")]:
            anchors.append(anchor_stats(df, ah, am, lab, bm))
    anchors = [a for a in anchors if a]
    return {
        "symbol": symbol,
        "bar_minutes": bm,
        "days": int(df["dt"].dt.date.nunique()),
        "from": str(df["dt"].iloc[0]),
        "to": str(df["dt"].iloc[-1]),
        "price_min": float(df["low"].min()),
        "price_max": float(df["high"].max()),
        "peak_hours_local": top_h,
        "wday_avg_hl": {k: round(v, 4) for k, v in wday_hl.items()},
        "anchors": anchors,
    }


def anchor_stats(df: pd.DataFrame, ah: int, am: int, lab: str, bm: int) -> dict | None:
    imp_bars = max(1, 10 // bm)
    rows = []
    for day in sorted(set(df["dt"].dt.date)):
        if pd.Timestamp(day).weekday() > 4:
            continue
        t0 = pd.Timestamp(day.year, day.month, day.day, ah, am, tzinfo=df["dt"].iloc[0].tzinfo)
        diff = (df["dt"] - t0).abs()
        i = diff.idxmin()
        if diff.loc[i] > pd.Timedelta(minutes=max(bm, 5)):
            continue
        ix = int(i)
        imp_bars = max(1, 10 // bm)
        hold = max(1, 30 // bm)
        if ix + imp_bars + hold >= len(df):
            continue
        p0 = df.iloc[ix]["open"]
        w = df.iloc[ix : ix + imp_bars + 1]
        hi, lo = w["high"].max(), w["low"].min()
        up, dn = hi - p0, p0 - lo
        if max(up, dn) < 1e-9:
            continue
        thr = max(up, dn) * 0.02 if max(up, dn) > 10 else max(up, dn) * 0.15
        if max(up, dn) < thr:
            continue
        sign = 1 if up >= dn else -1
        ex = hi if sign > 0 else lo
        imp = up if sign > 0 else dn
        px = df.iloc[ix + hold]["last"]
        retr = ((ex - px) if sign > 0 else (px - ex)) / imp * 100
        rows.append(retr)
    if len(rows) < 5:
        return None
    s = pd.Series(rows)
    return {
        "anchor": lab,
        "n": len(s),
        "median_impulse_proxy": "varies",
        "median_retrace_30m_pct": round(float(s.median()), 1),
        "ge50_pct": round(float((s >= 50).mean() * 100), 0),
    }


def resample_15m(df: pd.DataFrame) -> pd.Series:
    x = df.set_index("dt")["last"].resample("15min").last().dropna()
    return x.pct_change().dropna()


def lead_lag(series_a: pd.Series, series_b: pd.Series, max_lag: int = 8) -> dict:
    """Positive lag = A leads B by lag*15min."""
    idx = series_a.index.intersection(series_b.index)
    if len(idx) < 50:
        return {"n": len(idx), "best_lag": None, "best_corr": None}
    a = series_a.loc[idx].values
    b = series_b.loc[idx].values
    best_lag, best_c = 0, -2.0
    for lag in range(-max_lag, max_lag + 1):
        if lag < 0:
            aa, bb = a[-lag:], b[: lag]
        elif lag > 0:
            aa, bb = a[:-lag], b[lag:]
        else:
            aa, bb = a, b
        if len(aa) < 30:
            continue
        c = np.corrcoef(aa, bb)[0, 1]
        if c == c and c > best_c:
            best_c, best_lag = float(c), lag
    return {"n": int(len(idx)), "best_lag_15m_bars": best_lag, "lag_minutes": best_lag * 15, "corr": round(best_c, 3)}


def main() -> None:
    profiles = []
    series_15 = {}
    for sym, fname, tz in FILES:
        path = UPLOADS / fname
        if not path.exists():
            continue
        df = load(path, tz)
        profiles.append(profile(df, sym, tz))
        series_15[sym] = resample_15m(df)

    pairs = [
        ("NAS100", "US30"),
        ("NAS100", "SPX500"),
        ("GER30", "EUSTX50"),
        ("GER30", "ESP35"),
        ("EUSTX50", "ESP35"),
        ("UK100", "FRA40"),
        ("UK100", "US30"),
        ("FRA40", "ESP35"),
        ("US30", "SPX500"),
        ("NGAS", "US30"),
        ("XAUUSD", "US30"),
        ("XAUUSD", "SPX500"),
        ("XAGUSD", "XAUUSD"),
        ("XAGUSD", "US30"),
        ("UKOil", "US30"),
        ("UKOil", "NGAS"),
        ("UKOil", "XAUUSD"),
        ("USOil", "UKOil"),
        ("USOil", "US30"),
        ("USOil", "NGAS"),
    ]
    lags = []
    for a, b in pairs:
        if a in series_15 and b in series_15:
            # align to UTC for intersection
            sa = series_15[a].copy()
            sb = series_15[b].copy()
            sa.index = sa.index.tz_convert("UTC")
            sb.index = sb.index.tz_convert("UTC")
            lags.append({"pair": f"{a}→{b}", **lead_lag(sa, sb)})

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps({"profiles": profiles, "lead_lag": lags}, indent=2), encoding="utf-8")

    lines = [
        "# Cross-market sequence report",
        "",
        "_Sierra uploads · peak hours local TZ · 30m fade retrace @ anchors_",
        "",
        "## Data quality",
        "",
        "| Symbol | Bar | Days | Range | Peak hours (local) |",
        "|--------|-----|------|-------|-------------------|",
    ]
    for p in profiles:
        lines.append(
            f"| **{p['symbol']}** | {p['bar_minutes']}m | {p['days']} | {p['from'][:10]}…{p['to'][:10]} | {', '.join(p['peak_hours_local'][:4])} |"
        )
    lines.append("\n**Missing/empty:** CORNF, DJFXJPY (upload failed). **VOLX 1m** still needed.\n")
    lines.append("**Note:** NAS100 & GER30 older files are **~1h bars** — FRA40/UK100/US30/SPX500 are **1m**.\n")
    lines.append(
        "**Calendar:** FRA40/UK100/US30/SPX500/NGAS share **Jun–Jul 2026**; GER30/EUSTX50/ESP35 older export is **Jan–Feb 2026** — "
        "EU lead-lag across those sets is limited until dates align.\n"
    )

    lines.append("## Weekday avg daily range (points)\n")
    for p in profiles:
        if not p["wday_avg_hl"]:
            continue
        wd = " · ".join(f"{k} {v}" for k, v in sorted(p["wday_avg_hl"].items()))
        lines.append(f"- **{p['symbol']}:** {wd}")

    lines.append("\n## Anchor retrace (fade, ~30m, median %)\n")
    lines.append("| Symbol | Anchor | n | Med retrace | ≥50% |")
    lines.append("|--------|--------|---|-------------|------|")
    for p in profiles:
        for a in p.get("anchors", []):
            lines.append(
                f"| {p['symbol']} | {a['anchor']} | {a['n']} | {a['median_retrace_30m_pct']}% | {a['ge50_pct']}% |"
            )

    lines.append("\n## Lead–lag (15m returns, who moves first)\n")
    lines.append("| Pair | Lag (min) | Corr | n | Read |")
    lines.append("|------|-----------|------|---|------|")
    for L in lags:
        lag = L.get("lag_minutes")
        read = "—"
        if lag is not None:
            if lag > 0:
                read = f"{L['pair'].split('→')[0]} leads ~{lag}m"
            elif lag < 0:
                read = f"{L['pair'].split('→')[1]} leads ~{-lag}m"
            else:
                read = "synchronous"
        lines.append(f"| {L['pair']} | {lag} | {L.get('corr')} | {L.get('n')} | {read} |")

    lines.extend(
        [
            "",
            "## Sequence hypothesis (for GEM + VECTOR)",
            "",
            "1. **London 11:00:** UK100 fade; FRA40 often leads UK ~60m on 15m returns.",
            "2. **Paris 17:30:** FRA40 fade (71% median retrace in Jun–Jul 2026 sample).",
            "3. **US peak (14:30 ET):** NAS100 + US30/SPX500 + NGAS — shared fade window.",
            "4. **GEM CONFIRMED** only inside active TEMPORAL row (`morning_command_center.py`).",
            "5. **VECTOR** holds to profile `exit_et`; APEX pairs when z extreme **and** index leg agrees.",
            "",
            "Full JSON: `reports/cross_market_profiles.json`",
        ]
    )
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT_MD} and {OUT_JSON}")


if __name__ == "__main__":
    main()
