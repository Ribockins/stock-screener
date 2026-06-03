"""Build heat-map data from GEM scan results."""

from typing import List, Tuple

import pandas as pd

from src.gem.models import GEMAnalysis


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


def results_to_dataframe(results: List[GEMAnalysis]) -> pd.DataFrame:
    rows = []
    for r in results:
        name = r.symbol
        rows.append(
            {
                "Instrument": name,
                "RSI": round(r.rsi, 1),
                "Signal": signal_label(r),
                "SignalCode": signal_code(r),
                "GEM score": r.gem_score,
                "Exec": r.exec_state,
                "Price": round(r.price, 2),
            }
        )
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("SignalCode", ascending=False)
    return df


def heatmap_matrix(df: pd.DataFrame) -> Tuple[List[str], List[str], List[List[float]], List[List[str]]]:
    """Return y labels, x labels, z values, and hover text for Plotly heatmap."""
    if df.empty:
        return [], [], [], []

    y = df["Instrument"].tolist()
    x = ["RSI", "GEM signal"]
    z = []
    text = []
    for _, row in df.iterrows():
        z.append([float(row["RSI"]), float(row["SignalCode"])])
        text.append([f"RSI {row['RSI']}", row["Signal"]])
    return y, x, z, text
