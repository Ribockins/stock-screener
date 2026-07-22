#!/usr/bin/env python3
"""Backtest + chart APEX spread for a UK/CAC pair over recent days."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from src.apex.pair_spread import (  # noqa: E402
    calibrate_from_daily,
    simulate_spread_trades,
    spread_pnl_pct,
    spread_series,
    zscore,
)


def fetch_ohlc(symbols: list[str], period: str, interval: str) -> dict[str, pd.Series]:
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
    if len(symbols) == 1:
        sym = symbols[0]
        if "Close" in raw.columns:
            s = raw["Close"].copy()
            s.index = pd.to_datetime(s.index).tz_localize(None)
            out[sym] = s
        return out
    for sym in symbols:
        try:
            sub = raw[sym]
            if isinstance(sub, pd.DataFrame) and "Close" in sub.columns:
                s = sub["Close"].copy()
                s.index = pd.to_datetime(s.index).tz_localize(None)
                out[sym] = s
        except (KeyError, TypeError):
            continue
    return out


def plot_spread_chart(
    spread: pd.Series,
    z: pd.Series,
    trades: pd.DataFrame,
    uk: str,
    cac: str,
    beta: float,
    out_path: Path,
    entry_z: float,
) -> None:
    mu = float(spread.mean())
    sig = float(spread.std()) if spread.std() > 0 else 1.0

    fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True, gridspec_kw={"height_ratios": [2, 1]})
    ax0, ax1 = axes

    ax0.plot(spread.index, spread.values, color="#2563eb", linewidth=1.4, label="Spread (log diff)")
    ax0.axhline(mu, color="#64748b", linestyle="--", linewidth=1, label="Mean")
    ax0.axhline(mu + 2 * sig, color="#f59e0b", linestyle=":", linewidth=1, label="±2σ corridor")
    ax0.axhline(mu - 2 * sig, color="#f59e0b", linestyle=":", linewidth=1)
    ax0.fill_between(
        spread.index,
        mu - 2 * sig,
        mu + 2 * sig,
        color="#f59e0b",
        alpha=0.08,
    )

    if not trades.empty:
        for _, tr in trades.iterrows():
            color = "#16a34a" if tr["side"] == "LONG_SPREAD" else "#dc2626"
            ax0.scatter(tr["entry_time"], spread.get(tr["entry_time"], np.nan), marker="^", s=70, color=color, zorder=5)
            ax0.scatter(tr["exit_time"], spread.get(tr["exit_time"], np.nan), marker="v", s=70, color=color, zorder=5)

    ax0.set_ylabel("Spread")
    ax0.set_title(f"APEX spread: {uk} − {beta:.3f}×{cac} (difference / co-movement line)")
    ax0.legend(loc="upper left", fontsize=8)
    ax0.grid(True, alpha=0.25)

    ax1.plot(z.index, z.values, color="#7c3aed", linewidth=1.2, label="Z-score")
    ax1.axhline(0, color="#64748b", linestyle="--", linewidth=0.8)
    ax1.axhline(entry_z, color="#dc2626", linestyle=":", linewidth=0.8)
    ax1.axhline(-entry_z, color="#16a34a", linestyle=":", linewidth=0.8)
    ax1.set_ylabel("Z")
    ax1.set_xlabel("Time")
    ax1.legend(loc="upper left", fontsize=8)
    ax1.grid(True, alpha=0.25)

    fig.autofmt_xdate()
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--leg-a", dest="leg_a", default=None, help="Alias for first leg (with --leg-b)")
    parser.add_argument("--leg-b", dest="leg_b", default=None)
    parser.add_argument("--uk", default="RR.L")
    parser.add_argument("--cac", default="ACA.PA")
    parser.add_argument("--days", type=int, default=15)
    parser.add_argument("--beta", type=float, default=None, help="Fixed hedge; calibrate from daily if omitted")
    parser.add_argument("--interval", default="1h", choices=["1h", "1d"])
    parser.add_argument("--entry-z", type=float, default=2.0)
    parser.add_argument("--exit-z", type=float, default=0.5)
    parser.add_argument("--out-chart", type=Path, default=REPO / "reports/apex_rr_aca_spread_15d.png")
    parser.add_argument("--out-csv", type=Path, default=REPO / "reports/apex_rr_aca_backtest_15d.csv")
    args = parser.parse_args()

    uk, cac = args.uk, args.cac
    if args.leg_a and args.leg_b:
        uk, cac = args.leg_a, args.leg_b
    daily = fetch_ohlc([uk, cac], period="2y", interval="1d")
    if uk not in daily or cac not in daily:
        print("Missing daily data for calibration")
        return 1

    if args.beta is not None:
        beta = args.beta
        sp_d = spread_series(daily[uk], daily[cac], beta)
        mu, sig = float(sp_d.mean()), float(sp_d.std())
    else:
        beta, mu, sig = calibrate_from_daily(daily[uk], daily[cac])

    period = f"{max(args.days + 5, 20)}d"
    intraday = fetch_ohlc([uk, cac], period=period, interval=args.interval)
    if uk not in intraday or cac not in intraday:
        print("Missing intraday data")
        return 1

    frame = pd.concat([intraday[uk], intraday[cac]], axis=1, join="inner").dropna()
    frame.columns = [uk, cac]
    cutoff = frame.index.max() - pd.Timedelta(days=args.days)
    frame = frame[frame.index >= cutoff]
    if len(frame) < 10:
        print("Too few bars in test window")
        return 1

    spread = spread_series(frame[uk], frame[cac], beta)
    z = zscore(spread, mean=mu, std=sig)

    trades = simulate_spread_trades(z, entry_z=args.entry_z, exit_z=args.exit_z)
    trades = spread_pnl_pct(trades, spread)

    plot_spread_chart(
        spread,
        z,
        trades,
        uk,
        cac,
        beta,
        args.out_chart,
        args.entry_z,
    )

    series_out = pd.DataFrame({"spread": spread, "z": z})
    series_path = args.out_csv.with_name(args.out_csv.stem + "_series.csv")
    series_out.to_csv(series_path)
    trades.to_csv(args.out_csv, index=False)

    print(f"Pair: {uk} / {cac}")
    print(f"Beta: {beta:.4f} | calibration μ={mu:.6f} σ={sig:.6f}")
    print(f"Window: last {args.days}d @ {args.interval} | bars={len(spread)}")
    print(f"Chart: {args.out_chart}")
    print(f"Series CSV: {series_path}")
    print(f"Trades CSV: {args.out_csv}")
    print(f"Trades: {len(trades)}")
    if not trades.empty and trades["pnl_pct_log"].notna().any():
        pnl = trades["pnl_pct_log"].dropna()
        print(f"Win rate: {(pnl > 0).mean() * 100:.1f}% | sum log-PnL ≈ {pnl.sum():.3f}%")
        print(trades.to_string(index=False))
    else:
        print("No completed trades in window (z did not cross entry/exit rules).")
        print(f"Z range: {z.min():.2f} … {z.max():.2f} | last z={z.iloc[-1]:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
