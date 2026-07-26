#!/usr/bin/env python3
"""Find best ^GSPC (US500) hedge pair by correlation + mean-reverting spread corridor."""

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

US500 = "^GSPC"

# Exclude near-clones of the index (position scaling handles notional).
CANDIDATES = [
    "^DJI",
    "^IXIC",
    "^NDX",
    "QQQ",
    "DIA",
    "IWM",
    "^RUT",
    "XLF",
    "XLK",
    "XLE",
    "XLV",
    "XLI",
    "^NYA",
    "^VIX",
]


def fetch_closes(symbols: list[str], period: str, interval: str) -> pd.DataFrame:
    import yfinance as yf

    raw = yf.download(
        symbols,
        period=period,
        interval=interval,
        group_by="ticker",
        auto_adjust=True,
        progress=False,
        threads=True,
    )
    out: dict[str, pd.Series] = {}
    for sym in symbols:
        try:
            sub = raw[sym]
            if isinstance(sub, pd.DataFrame) and "Close" in sub.columns:
                s = sub["Close"].copy()
                s.index = pd.to_datetime(s.index).tz_localize(None)
                out[sym] = s
        except (KeyError, TypeError):
            continue
    return pd.DataFrame(out)


def hedge_beta(y: np.ndarray, x: np.ndarray) -> float:
    lx, ly = np.log(x.astype(float)), np.log(y.astype(float))
    xm, ym = lx - lx.mean(), ly - ly.mean()
    d = float(np.dot(xm, xm))
    return float(np.dot(xm, ym) / d) if d > 0 else float("nan")


def hurst(ts: np.ndarray, max_lag: int = 20) -> float:
    ts = ts[np.isfinite(ts)]
    if len(ts) < max_lag * 3:
        return float("nan")
    lags = range(2, max_lag)
    tau = [np.std(ts[lag:] - ts[:-lag]) for lag in lags]
    reg = np.polyfit(np.log(list(lags)), np.log(tau), 1)
    return float(reg[0])


def analyze(leg: str, period: str, interval: str) -> dict | None:
    from statsmodels.tsa.stattools import coint

    px = fetch_closes([US500, leg], period=period, interval=interval)
    if US500 not in px.columns or leg not in px.columns:
        return None
    df = px[[US500, leg]].dropna()
    if len(df) < 80:
        return None
    y, x = df[US500].astype(float), df[leg].astype(float)
    if (y <= 0).any() or (x <= 0).any():
        return None
    ly, lx = np.log(y.values), np.log(x.values)
    corr = float(np.corrcoef(ly, lx)[0, 1])
    beta = hedge_beta(y.values, x.values)
    spread = ly - beta * lx
    sp = pd.Series(spread, index=df.index)
    mu, sig = float(sp.mean()), float(sp.std())
    if sig <= 0:
        return None
    z = (sp - mu) / sig
    try:
        coint_p = float(coint(ly, lx)[1])
    except Exception:
        coint_p = 1.0
    h = hurst(spread)
    oscill = float((np.sign(z.iloc[:-1].values) != np.sign(z.iloc[1:].values).astype(bool)).mean())
    wide = float((z.abs() >= 1.25).mean())
    cross = float((z.shift(1) * z < 0).sum()) / max(len(z) - 1, 1)
    return {
        "leg": leg,
        "n": len(df),
        "corr": corr,
        "beta": beta,
        "coint_p": coint_p,
        "hurst": h,
        "zero_cross": cross,
        "sign_flip": oscill,
        "wide_125": wide,
        "z_range": float(z.max() - z.min()),
        "last_z": float(z.iloc[-1]),
        "mean_abs_dz": float(z.diff().abs().mean()),
    }


def score_row(r: pd.Series) -> float:
    p = r["coint_p"]
    h = r.get("hurst", 0.5)
    return (
        abs(r["corr"]) * 3.0
        + max(0.0, 1.0 - p) * 8.0
        + r["zero_cross"] * 10.0
        + r["wide_125"] * 12.0
        + r["mean_abs_dz"] * 4.0
        + max(0.0, 0.55 - h) * 15.0  # prefer mean-reverting (H < 0.5)
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=REPO / "reports/us500_pair_screen.csv")
    args = parser.parse_args()

    rows: list[dict] = []
    for leg in CANDIDATES:
        d = analyze(leg, "2y", "1d")
        h1 = analyze(leg, "60d", "1h")
        if d is None:
            continue
        row = {**d, "interval": "1d"}
        if h1:
            row["h1_wide_125"] = h1["wide_125"]
            row["h1_zero_cross"] = h1["zero_cross"]
        row["score"] = score_row(pd.Series(d))
        rows.append(row)

    if not rows:
        print("No pairs found")
        return 1
    df = pd.DataFrame(rows).sort_values("score", ascending=False)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"US500 anchor: {US500}")
    print(f"Wrote {args.out}\n")
    cols = ["leg", "score", "corr", "beta", "coint_p", "hurst", "zero_cross", "wide_125", "z_range", "last_z"]
    print(df[cols].head(8).to_string(index=False))
    best = df.iloc[0]
    print(
        f"\nRecommended pair: {US500} + {best['leg']} | beta={best['beta']:.4f} "
        f"(scale leg B = leg A × beta in log-hedge; lots free)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
