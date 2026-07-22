#!/usr/bin/env python3
"""Screen UK100 x CAC40 pairs for spread / cointegration (APEX adult layer)."""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def load_tickers(path: Path) -> list[str]:
    out: list[str] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        out.append(line)
    # preserve order, dedupe
    seen: set[str] = set()
    deduped: list[str] = []
    for t in out:
        if t not in seen:
            seen.add(t)
            deduped.append(t)
    return deduped


def fetch_closes(symbols: list[str], period: str = "2y") -> pd.DataFrame:
    import yfinance as yf

    if not symbols:
        return pd.DataFrame()
    # yfinance batch download
    raw = yf.download(
        symbols,
        period=period,
        interval="1d",
        group_by="ticker",
        auto_adjust=True,
        progress=False,
        threads=True,
    )
    if raw.empty:
        return pd.DataFrame()
    if len(symbols) == 1:
        s = symbols[0]
        if "Close" in raw.columns:
            return raw[["Close"]].rename(columns={"Close": s})
        return pd.DataFrame()
    closes: dict[str, pd.Series] = {}
    for sym in symbols:
        try:
            sub = raw[sym]
            if isinstance(sub, pd.DataFrame) and "Close" in sub.columns:
                closes[sym] = sub["Close"]
        except (KeyError, TypeError):
            continue
    if not closes:
        # flat columns fallback
        if "Close" in raw.columns:
            return raw[["Close"]]
        return pd.DataFrame()
    df = pd.DataFrame(closes)
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df


def hedge_ratio(y: np.ndarray, x: np.ndarray) -> float:
    """OLS: log(y) ~ alpha + beta * log(x)."""
    lx = np.log(x)
    ly = np.log(y)
    x_m = lx - lx.mean()
    y_m = ly - ly.mean()
    denom = np.dot(x_m, x_m)
    if denom <= 0:
        return float("nan")
    return float(np.dot(x_m, y_m) / denom)


def spread_half_life(spread: pd.Series) -> float:
    s = spread.dropna()
    if len(s) < 30:
        return float("nan")
    lag = s.shift(1).iloc[1:]
    delta = s.diff().iloc[1:]
    if lag.std() == 0:
        return float("nan")
    beta = np.linalg.lstsq(lag.values.reshape(-1, 1), delta.values, rcond=None)[0][0]
    if beta >= 0:
        return float("inf")
    hl = -math.log(2) / beta
    return float(hl)


def analyze_pair(
    a: pd.Series,
    b: pd.Series,
    min_obs: int = 200,
) -> dict | None:
    from statsmodels.tsa.stattools import coint

    frame = pd.concat([a, b], axis=1, join="inner").dropna()
    if len(frame) < min_obs:
        return None
    y = frame.iloc[:, 0].astype(float)
    x = frame.iloc[:, 1].astype(float)
    if (y <= 0).any() or (x <= 0).any():
        return None

    ly = np.log(y.values)
    lx = np.log(x.values)
    corr = float(np.corrcoef(ly, lx)[0, 1])
    beta = hedge_ratio(y.values, x.values)
    if not math.isfinite(beta):
        return None
    spread = pd.Series(ly - beta * lx, index=frame.index)
    spread_z = (spread - spread.mean()) / spread.std() if spread.std() > 0 else spread * 0
    try:
        _t, pvalue, _crit = coint(ly, lx)
        pvalue = float(pvalue)
    except Exception:
        pvalue = 1.0
    hl = spread_half_life(spread)
    # fraction of days |z|>2 (tradeable extremes)
    tail = float((spread_z.abs() > 2.0).mean()) if len(spread_z) else 0.0
    return {
        "n": len(frame),
        "corr": corr,
        "beta": beta,
        "coint_p": pvalue,
        "half_life": hl,
        "spread_std": float(spread.std()),
        "z_tail_frac": tail,
        "last_z": float(spread_z.iloc[-1]),
    }


def rank_score(row: pd.Series) -> float:
    """Higher = better pair for mean-reversion spread trading."""
    p = row["coint_p"]
    corr = abs(row["corr"])
    hl = row["half_life"]
    if not math.isfinite(hl) or hl <= 0:
        hl_penalty = -10.0
    elif hl > 120:
        hl_penalty = -8.0
    elif hl < 3:
        hl_penalty = -3.0
    elif 5 <= hl <= 60:
        hl_penalty = 3.0
    else:
        hl_penalty = -1.0
    coint_score = max(0.0, 1.0 - p) * 10.0
    if p > 0.10:
        coint_score *= 0.3
    corr_score = corr * 5.0
    tail = row.get("z_tail_frac", 0) or 0
    tail_score = min(tail * 20.0, 2.0)
    return coint_score + corr_score + hl_penalty + tail_score


def main() -> int:
    parser = argparse.ArgumentParser(description="APEX pair screen UK100 x CAC40")
    parser.add_argument("--uk", type=Path, default=REPO / "data/stocks/uk100.txt")
    parser.add_argument("--cac", type=Path, default=REPO / "data/stocks/cac40.txt")
    parser.add_argument("--period", default="2y")
    parser.add_argument("--top", type=int, default=15)
    parser.add_argument("--out", type=Path, default=REPO / "reports/apex_pair_screen.csv")
    args = parser.parse_args()

    uk = load_tickers(args.uk)
    cac = load_tickers(args.cac)
    print(f"UK tickers: {len(uk)}, CAC tickers: {len(cac)}")

    print("Downloading UK closes…")
    uk_px = fetch_closes(uk, period=args.period)
    print("Downloading CAC closes…")
    cac_px = fetch_closes(cac, period=args.period)

    uk_ok = [c for c in uk_px.columns if uk_px[c].notna().sum() >= 200]
    cac_ok = [c for c in cac_px.columns if cac_px[c].notna().sum() >= 200]
    print(f"UK with enough history: {len(uk_ok)}, CAC: {len(cac_ok)}")

    rows: list[dict] = []
    total = len(uk_ok) * len(cac_ok)
    done = 0
    for u in uk_ok:
        for c in cac_ok:
            done += 1
            if done % 500 == 0:
                print(f"  pairs {done}/{total}…")
            stats = analyze_pair(uk_px[u], cac_px[c])
            if stats is None:
                continue
            if stats["corr"] < 0.5:
                continue
            row = {"uk": u, "cac": c, **stats}
            row["score"] = rank_score(pd.Series(row))
            rows.append(row)

    if not rows:
        print("No pairs passed filters.")
        return 1

    df = pd.DataFrame(rows).sort_values("score", ascending=False)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"\nWrote {args.out}")
    print("\nTop pairs (UK leg vs CAC leg — spread = log(UK) - beta*log(CAC)):\n")
    cols = [
        "uk",
        "cac",
        "score",
        "corr",
        "coint_p",
        "beta",
        "half_life",
        "last_z",
        "n",
    ]
    print(df[cols].head(args.top).to_string(index=False))

    best = df.iloc[0]
    print(
        f"\nBest pair: {best['uk']} + {best['cac']} | "
        f"score={best['score']:.2f} corr={best['corr']:.3f} "
        f"coint p={best['coint_p']:.4f} beta={best['beta']:.3f} "
        f"half-life={best['half_life']:.1f}d last_z={best['last_z']:.2f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
