#!/usr/bin/env python3
"""
Screen intra-market pairs (UK100-only or CAC40-only) for cap-aware spread corridors.

Optimises for a stable, mean-reverting difference line and session-friendly wider bands.
"""

from __future__ import annotations

import argparse
import itertools
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.screen_apex_pairs import analyze_pair, fetch_closes, load_tickers  # noqa: E402


def fetch_market_caps(symbols: list[str]) -> dict[str, float]:
    import yfinance as yf

    caps: dict[str, float] = {}
    chunk = 40
    for i in range(0, len(symbols), chunk):
        batch = symbols[i : i + chunk]
        for sym in batch:
            try:
                t = yf.Ticker(sym)
                cap = None
                fi = getattr(t, "fast_info", None)
                if fi is not None:
                    cap = getattr(fi, "market_cap", None) or getattr(fi, "marketCap", None)
                if cap is None:
                    info = t.info or {}
                    cap = info.get("marketCap")
                if cap and cap > 0:
                    caps[sym] = float(cap)
            except Exception:
                continue
    return caps


def cap_blend_beta(beta_ols: float, mcap_a: float, mcap_b: float) -> float:
    """Blend statistical hedge with cap ratio (log-mcap) for balanced notional feel."""
    if mcap_a <= 0 or mcap_b <= 0 or not math.isfinite(beta_ols):
        return beta_ols
    cap_ratio = math.log(mcap_a / mcap_b)
    # pull beta toward 1.0 by cap similarity; large cap gap -> more weight on OLS
    w = min(0.45, abs(cap_ratio) * 0.08)
    beta_cap = 1.0 + 0.35 * cap_ratio  # soft cap anchor
    return (1 - w) * beta_ols + w * beta_cap


def corridor_metrics(
    a: pd.Series,
    b: pd.Series,
    beta: float,
    wide_entry_z: float = 1.25,
) -> dict | None:
    frame = pd.concat([a, b], axis=1, join="inner").dropna().tail(252)
    if len(frame) < 120:
        return None
    y = frame.iloc[:, 0].astype(float)
    x = frame.iloc[:, 1].astype(float)
    if (y <= 0).any() or (x <= 0).any():
        return None
    spread = np.log(y) - beta * np.log(x)
    sp = pd.Series(spread, index=frame.index)
    mu, sig = float(sp.mean()), float(sp.std())
    if sig <= 0:
        return None
    z = (sp - mu) / sig
    # even corridor: low drift, bounded range
    t = np.arange(len(sp), dtype=float)
    slope = float(np.polyfit(t, sp.values, 1)[0])
    drift_penalty = abs(slope) / sig * 252
    inside_wide = float((z.abs() <= wide_entry_z * 1.6).mean())
    cross_zero = float((z.shift(1) * z < 0).sum()) / max(len(z) - 1, 1)
    swing = float(z.diff().abs().mean())
    wide_hits = float((z.abs() >= wide_entry_z).mean())
    range_width = float(z.max() - z.min())
    return {
        "drift_per_sigma_y": drift_penalty,
        "inside_wide_frac": inside_wide,
        "zero_cross_rate": cross_zero,
        "mean_abs_dz": swing,
        "wide_hit_frac": wide_hits,
        "z_range": range_width,
        "spread_std": sig,
    }


def rank_intra(row: pd.Series, wide_z: float) -> float:
    base = 0.0
    p = row["coint_p"]
    if p < 0.05:
        base += 8
    elif p < 0.12:
        base += 5
    elif p < 0.25:
        base += 2
    hl = row["half_life"]
    if math.isfinite(hl) and 4 <= hl <= 45:
        base += 4
    elif math.isfinite(hl) and hl <= 90:
        base += 1
    corr = abs(row["corr"])
    base += corr * 3
    # session / wide corridor friendly
    base += row.get("mean_abs_dz", 0) * 4
    base += row.get("wide_hit_frac", 0) * 12
    base += row.get("zero_cross_rate", 0) * 6
    base -= row.get("drift_per_sigma_y", 0) * 0.5
    ma = row.get("mcap_a_bn") or row.get("mcap_a")
    mb = row.get("mcap_b_bn") or row.get("mcap_b")
    if ma and mb and ma > 0 and mb > 0:
        cap_skew = abs(math.log(ma / mb))
        base += max(0.0, 2.5 - cap_skew)  # reward similar market caps
    if row.get("z_range", 0) < wide_z * 1.5:
        base -= 3
    if row.get("inside_wide_frac", 0) > 0.85:
        base += 2
    return base


def pick_disjoint_pairs(df: pd.DataFrame, k: int = 2) -> pd.DataFrame:
    chosen: list[pd.Series] = []
    used: set[str] = set()
    for _, row in df.iterrows():
        a, b = row["leg_a"], row["leg_b"]
        if a in used or b in used:
            continue
        chosen.append(row)
        used.add(a)
        used.add(b)
        if len(chosen) >= k:
            break
    return pd.DataFrame(chosen)


def screen_universe(
    tickers: list[str],
    px: pd.DataFrame,
    caps: dict[str, float],
    wide_z: float,
    label: str,
) -> pd.DataFrame:
    ok = [c for c in tickers if c in px.columns and px[c].notna().sum() >= 200]
    rows: list[dict] = []
    for a, b in itertools.combinations(ok, 2):
        if a not in caps or b not in caps:
            continue
        stats = analyze_pair(px[a], px[b])
        if stats is None or stats["corr"] < 0.75:
            continue
        if stats["coint_p"] > 0.35:
            continue
        hl = stats["half_life"]
        if not math.isfinite(hl):
            hl = 9999.0
        if hl < 2:
            continue
        beta_blend = cap_blend_beta(stats["beta"], caps[a], caps[b])
        cm = corridor_metrics(px[a], px[b], beta_blend, wide_entry_z=wide_z)
        if cm is None:
            continue
        if hl > 120 and cm.get("wide_hit_frac", 0) < 0.18:
            continue
        row = {
            "universe": label,
            "leg_a": a,
            "leg_b": b,
            "mcap_a_bn": caps[a] / 1e9,
            "mcap_b_bn": caps[b] / 1e9,
            "beta_ols": stats["beta"],
            "beta_cap_blend": beta_blend,
            **stats,
            **cm,
        }
        row["score"] = rank_intra(pd.Series(row), wide_z)
        rows.append(row)
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("score", ascending=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wide-z", type=float, default=1.25, help="Wider session entry band (vs 2.0)")
    parser.add_argument("--pairs", type=int, default=2, help="Disjoint pairs per universe (2 pairs = 4 names)")
    parser.add_argument("--period", default="2y")
    parser.add_argument("--out", type=Path, default=REPO / "reports/apex_intra_screen.csv")
    args = parser.parse_args()

    uk = load_tickers(REPO / "data/stocks/uk100.txt")
    cac = load_tickers(REPO / "data/stocks/cac40.txt")

    print("Downloading prices…")
    uk_px = fetch_closes(uk, period=args.period)
    cac_px = fetch_closes(cac, period=args.period)

    print("Fetching market caps (UK)…")
    uk_caps = fetch_market_caps([c for c in uk_px.columns])
    print(f"  UK caps: {len(uk_caps)}")
    print("Fetching market caps (CAC)…")
    cac_caps = fetch_market_caps([c for c in cac_px.columns])
    print(f"  CAC caps: {len(cac_caps)}")

    uk_df = screen_universe(uk, uk_px, uk_caps, args.wide_z, "UK100")
    cac_df = screen_universe(cac, cac_px, cac_caps, args.wide_z, "CAC40")

    uk_pick = pick_disjoint_pairs(uk_df, args.pairs)
    cac_pick = pick_disjoint_pairs(cac_df, args.pairs)

    out = pd.concat([uk_df, cac_df], ignore_index=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False)

    print(f"\nWrote full scan: {args.out}")
    cols = [
        "leg_a",
        "leg_b",
        "score",
        "corr",
        "coint_p",
        "beta_cap_blend",
        "half_life",
        "wide_hit_frac",
        "mean_abs_dz",
        "z_range",
        "last_z",
    ]

    print(f"\n=== UK100 — top {args.pairs} disjoint pairs (wide z={args.wide_z}) ===")
    if uk_pick.empty:
        print("(none)")
    else:
        print(uk_pick[cols + ["mcap_a_bn", "mcap_b_bn"]].to_string(index=False))

    print(f"\n=== CAC40 — top {args.pairs} disjoint pairs (wide z={args.wide_z}) ===")
    if cac_pick.empty:
        print("(none)")
    else:
        print(cac_pick[cols + ["mcap_a_bn", "mcap_b_bn"]].to_string(index=False))

    picks_path = args.out.with_name("apex_intra_picks.json")
    import json

    payload = {
        "wide_entry_z": args.wide_z,
        "uk_pairs": uk_pick[["leg_a", "leg_b", "beta_cap_blend", "score"]].to_dict(orient="records"),
        "cac_pairs": cac_pick[["leg_a", "leg_b", "beta_cap_blend", "score"]].to_dict(orient="records"),
    }
    picks_path.write_text(json.dumps(payload, indent=2))
    print(f"\nPicks JSON: {picks_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
