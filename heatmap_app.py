#!/usr/bin/env python3
"""
GEM Logic Heatmap — install on your PC, open in browser.

Run:  START_HEATMAP.bat   (Windows)
      ./start_heatmap.sh    (Mac/Linux)
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.gem_platform import GEMPlatform
from src.heatmap_data import heatmap_matrix, results_to_dataframe, signal_label
from src.watchlist import load_watchlist, watchlist_path

st.set_page_config(
    page_title="GEM Logic Heatmap",
    page_icon="📊",
    layout="wide",
)

# Colours: red = bearish, green = bullish (GEM Logic style)
SIGNAL_COLORS = [
    [0.0, "#8b0032"],   # strong sell
    [0.35, "#c62828"],
    [0.45, "#424242"],  # neutral
    [0.55, "#2e7d32"],
    [1.0, "#00c896"],   # emerald
]


@st.cache_resource
def get_platform():
    return GEMPlatform()


def make_signal_heatmap(df: pd.DataFrame) -> go.Figure:
    y, x, z, text = heatmap_matrix(df)
    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=x,
            y=y,
            text=text,
            texttemplate="%{text}",
            textfont={"size": 11},
            colorscale=SIGNAL_COLORS,
            zmid=0,
            zmin=-4,
            zmax=4,
            colorbar=dict(
                title="Signal",
                tickvals=[-4, -2, 0, 2, 4],
                ticktext=["RUBY GEM", "Sell setup", "—", "Buy setup", "EMERALD GEM"],
            ),
        )
    )
    fig.update_layout(
        title="GEM signal heatmap (green = bullish, red = bearish)",
        height=max(400, len(y) * 28),
        margin=dict(l=120, r=40, t=60, b=40),
        yaxis=dict(autorange="reversed"),
    )
    return fig


def main():
    st.title("GEM Logic Heatmap")
    st.caption("Your watchlist · live data · same signals as cloud scans (EMERALD / RUBY GEM)")

    wl = load_watchlist()
    n = len(wl.get("instruments", []))
    st.sidebar.header("Controls")
    st.sidebar.write(f"**Instruments:** {n}")
    st.sidebar.write(f"**List file:** `{watchlist_path()}`")
    auto = st.sidebar.checkbox("Auto-refresh", value=False)
    mins = st.sidebar.number_input("Refresh every (minutes)", 1, 60, int(wl.get("refresh_minutes", 5)))
    run = st.sidebar.button("Scan now", type="primary", use_container_width=True)

    if auto:
        st.sidebar.info(f"Refreshing every {mins} min…")
        st.autorefresh(interval=mins * 60 * 1000, key="gem_refresh")

    if run or auto or "last_df" not in st.session_state:
        with st.spinner("Fetching live prices and running GEM Logic… (1–3 min)"):
            try:
                results = get_platform().scan_watchlist(wl)
                st.session_state["last_df"] = results_to_dataframe(results)
                st.session_state["last_results"] = results
            except Exception as e:
                st.error(f"Scan failed: {e}")
                st.stop()

    df = st.session_state.get("last_df")
    if df is None or df.empty:
        st.warning("Click **Scan now** in the sidebar to load signals.")
        st.stop()

    # Summary chips
    actionable = df[df["SignalCode"].abs() >= 2]
    c1, c2, c3 = st.columns(3)
    c1.metric("Scanned", len(df))
    c2.metric("Actionable", len(actionable))
    emerald = len(df[df["Signal"] == "EMERALD GEM"])
    ruby = len(df[df["Signal"] == "RUBY GEM"])
    c3.metric("EMERALD / RUBY", f"{emerald} / {ruby}")

    st.plotly_chart(make_signal_heatmap(df), use_container_width=True)

    st.subheader("Detail table")
    display = df[["Instrument", "RSI", "Signal", "GEM score", "Exec", "Price"]].copy()
    st.dataframe(display, use_container_width=True, hide_index=True)

    with st.expander("Legend (what colours mean)"):
        st.markdown(
            """
| Colour | Meaning |
|--------|---------|
| **Bright green** | **EMERALD GEM** — oversold + bullish divergence + bullish candle |
| **Bright red** | **RUBY GEM** — overbought + bearish divergence + bearish candle |
| Light green | Buy setup / long entry / oversold |
| Light red | Sell setup / short entry / overbought |
| Grey | No strong signal |

**RSI column** in the heatmap shows the actual RSI number (0–100).
            """
        )


if __name__ == "__main__":
    main()
