"""Build heat-map and checklist tables from GEM multi-timeframe scans."""

from typing import List, Tuple

import pandas as pd

from src.gem.models import GEMAnalysis
from src.gem.timeframes import DEFAULT_TIMEFRAMES, TF_SHORT
from src.gem_platform import InstrumentMTFScan
from src.gem_strength import STRENGTH_RANK, rate_gem_analysis, strength_badge


def signal_code(analysis: GEMAnalysis) -> int:
    """Numeric code for heat-map colour (-4 sell … +4 buy)."""
    if analysis.buy_gem:
        return 4
    if analysis.sell_gem:
        return -4
    if analysis.buy_entry:
        return 3
    if analysis.sell_entry:
        return -3
    if analysis.buy_setup:
        return 2
    if analysis.sell_setup:
        return -2
    if analysis.in_oversold:
        return 1
    if analysis.in_overbought:
        return -1
    return 0


def signal_label(analysis: GEMAnalysis) -> str:
    if analysis.buy_gem:
        return "EMERALD GEM"
    if analysis.sell_gem:
        return "RUBY GEM"
    if analysis.buy_entry:
        return "LONG ENTRY"
    if analysis.sell_entry:
        return "SHORT ENTRY"
    if analysis.buy_setup:
        return "BUY SETUP"
    if analysis.sell_setup:
        return "SELL SETUP"
    if analysis.in_oversold:
        return "Oversold"
    if analysis.in_overbought:
        return "Overbought"
    return "—"


def _strength_to_code(strength: str, direction: str, score: int) -> float:
    """Map strength tier to heatmap z in [-4, 4]."""
    rank = STRENGTH_RANK.get(strength, 0)
    if rank == 0 or direction == "NEUTRAL":
        return 0.0
    sign = -1.0 if direction == "BEARISH" else 1.0
    if score < 0:
        sign = -1.0
    elif score > 0:
        sign = 1.0
    tier_map = {1: 0.8, 2: 1.6, 3: 2.5, 4: 3.2, 5: 4.0}
    return sign * tier_map.get(rank, 1.0)


def mtf_rows_to_dataframe(scans: List[InstrumentMTFScan]) -> pd.DataFrame:
    """Wide table: instrument × TF signal strength + checklist."""
    tfs = DEFAULT_TIMEFRAMES
    rows = []
    for s in scans:
        cr = s.combined_rating
        cl = s.checklist
        row = {
            "Instrument": s.display_name,
            "Symbol": s.symbol,
            "MTF strength": cr.strength if cr else "NONE",
            "MTF badge": strength_badge(cr.strength) if cr else "—",
            "Direction": cr.direction if cr else "NEUTRAL",
            "MTF score": cr.score if cr else 0,
            "Headline": cr.signal_name if cr else "—",
            "Checklist": f"{cl.score}/6" if cl else "—",
            "Trade OK": "✅" if cl and cl.trade_ok else "—",
            "Check summary": cl.summary if cl else "—",
        }
        for tf in tfs:
            col = TF_SHORT.get(tf, tf)
            r = s.ratings.get(tf)
            a = s.analyses.get(tf)
            if r and a:
                row[f"{col} signal"] = r.signal_name
                row[f"{col} str"] = r.strength
                row[f"{col} RSI"] = round(a.rsi, 1)
                row[f"{col} z"] = _strength_to_code(r.strength, r.direction, r.score)
            else:
                row[f"{col} signal"] = "—"
                row[f"{col} str"] = "NONE"
                row[f"{col} RSI"] = None
                row[f"{col} z"] = 0.0
        rows.append(row)

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("MTF score", key=lambda s: s.abs(), ascending=False)
    return df


def results_to_dataframe(results: List[GEMAnalysis]) -> pd.DataFrame:
    """Legacy single-TF table."""
    rows = []
    for r in results:
        rating = rate_gem_analysis(r, "60")
        rows.append(
            {
                "Instrument": r.symbol,
                "RSI": round(r.rsi, 1),
                "Signal": signal_label(r),
                "SignalCode": signal_code(r),
                "Strength": rating.strength,
                "Direction": rating.direction,
                "GEM score": r.gem_score,
                "Exec": r.exec_state,
                "Price": round(r.price, 2),
            }
        )
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("SignalCode", ascending=False)
    return df


def mtf_signal_heatmap_matrix(
    df: pd.DataFrame,
) -> Tuple[List[str], List[str], List[List[float]], List[List[str]]]:
    if df.empty:
        return [], [], [], []
    tfs = [TF_SHORT.get(tf, tf) for tf in DEFAULT_TIMEFRAMES]
    y = df["Instrument"].tolist()
    z, text = [], []
    for _, row in df.iterrows():
        z.append([float(row.get(f"{tf} z", 0)) for tf in tfs])
        text.append([f"{row.get(f'{tf} signal', '—')} ({row.get(f'{tf} str', '')})" for tf in tfs])
    return y, tfs, z, text


def mtf_strength_bar_matrix(df: pd.DataFrame) -> Tuple[List[str], List[float], List[str]]:
    if df.empty:
        return [], [], []
    y = df["Instrument"].tolist()
    z = [float(s) for s in df["MTF score"]]
    text = [f"{row['MTF badge']} {row['MTF strength']} — {row['Headline']}" for _, row in df.iterrows()]
    return y, z, text


def rsi_heatmap_matrix_mtf(df: pd.DataFrame) -> Tuple[List[str], List[str], List[List[float]]]:
    if df.empty:
        return [], [], []
    tfs = [TF_SHORT.get(tf, tf) for tf in DEFAULT_TIMEFRAMES]
    y = df["Instrument"].tolist()
    z = [[float(row.get(f"{tf} RSI") or 50) for tf in tfs] for _, row in df.iterrows()]
    return y, tfs, z


def signal_heatmap_matrix(df: pd.DataFrame) -> Tuple[List[str], List[List[float]], List[str]]:
    if df.empty:
        return [], [], []
    y = df["Instrument"].tolist()
    z = [[float(c)] for c in df["SignalCode"]]
    text = df["Signal"].tolist()
    return y, z, text


def rsi_heatmap_matrix(df: pd.DataFrame) -> Tuple[List[str], List[List[float]]]:
    if df.empty:
        return [], []
    y = df["Instrument"].tolist()
    z = [[float(r)] for r in df["RSI"]]
    return y, z
