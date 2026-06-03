#!/usr/bin/env python3
"""
GEM Logic Heatmap — multi-timeframe strength + trade checklist.

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
from src.heatmap_data import (
    mtf_rows_to_dataframe,
    mtf_signal_heatmap_matrix,
    mtf_strength_bar_matrix,
    rsi_heatmap_matrix_mtf,
)
from src.watchlist import load_watchlist, watchlist_path

st.set_page_config(
    page_title="GEM Logic Heatmap",
    page_icon="📊",
    layout="wide",
)

STRENGTH_COLORS = [
    [0.0, "#8b0032"],
    [0.35, "#c62828"],
    [0.45, "#424242"],
    [0.55, "#2e7d32"],
    [1.0, "#00c896"],
]


@st.cache_resource
def get_platform():
    return GEMPlatform()


def make_mtf_strength_heatmap(df: pd.DataFrame) -> go.Figure:
    y, x, z, text = mtf_signal_heatmap_matrix(df)
    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=x,
            y=y,
            text=text,
            texttemplate="%{text}",
            textfont={"size": 10},
            colorscale=STRENGTH_COLORS,
            zmid=0,
            zmin=-4,
            zmax=4,
            colorbar=dict(
                title="Strength",
                tickvals=[-4, -2, 0, 2, 4],
                ticktext=["PREMIUM bear", "STRONG bear", "—", "STRONG bull", "PREMIUM bull"],
            ),
        )
    )
    fig.update_layout(
        title="Signal strength by timeframe (★ = stronger GEM alignment)",
        height=max(360, len(y) * 32),
        margin=dict(l=130, r=40, t=50, b=30),
        yaxis=dict(autorange="reversed"),
    )
    return fig


def make_mtf_score_bar(df: pd.DataFrame) -> go.Figure:
    y, z, text = mtf_strength_bar_matrix(df)
    colors = ["#00c896" if v >= 0 else "#c62828" for v in z]
    fig = go.Figure(
        data=go.Bar(
            x=z,
            y=y,
            orientation="h",
            text=text,
            textposition="outside",
            marker_color=colors,
        )
    )
    fig.update_layout(
        title="Combined MTF score (−100 bear … +100 bull)",
        height=max(320, len(y) * 28),
        margin=dict(l=130, r=80, t=50, b=30),
        xaxis=dict(range=[-105, 105]),
        yaxis=dict(autorange="reversed"),
    )
    return fig


def make_rsi_mtf_heatmap(df: pd.DataFrame) -> go.Figure:
    y, x, z = rsi_heatmap_matrix_mtf(df)
    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=x,
            y=y,
            text=z,
            texttemplate="%{z:.0f}",
            textfont={"size": 11},
            colorscale=[
                [0.0, "#00c896"],
                [0.28, "#a5d6a7"],
                [0.45, "#eeeeee"],
                [0.55, "#eeeeee"],
                [0.72, "#ef9a9a"],
                [1.0, "#c62828"],
            ],
            zmin=0,
            zmax=100,
            colorbar=dict(title="RSI"),
        )
    )
    fig.update_layout(
        title="RSI (14) across timeframes",
        height=max(360, len(y) * 32),
        margin=dict(l=130, r=40, t=50, b=30),
        yaxis=dict(autorange="reversed"),
    )
    return fig


def main():
    st.title("GEM Logic Heatmap")
    st.caption("Your instruments · 15m / 1h / 4h / Daily · strength tiers + 6-point trade checklist")

    wl = load_watchlist()
    n = len(wl.get("instruments", []))
    st.sidebar.header("Controls")
    st.sidebar.write(f"**Instruments:** {n}")
    st.sidebar.write("**TFs:** M15, H1, H4, D1")
    st.sidebar.write(f"**List:** `{watchlist_path()}`")
    auto = st.sidebar.checkbox("Auto-refresh", value=False)
    mins = st.sidebar.number_input("Refresh every (minutes)", 1, 60, int(wl.get("refresh_minutes", 5)))
    run = st.sidebar.button("Scan now", type="primary", use_container_width=True)

    if auto:
        st.sidebar.info(f"Refreshing every {mins} min…")
        st.autorefresh(interval=mins * 60 * 1000, key="gem_refresh")

    if run or auto or "last_mtf_df" not in st.session_state:
        with st.spinner("Scanning 4 timeframes per instrument (2–5 min)…"):
            try:
                scans = get_platform().scan_watchlist_mtf(wl)
                st.session_state["last_mtf_df"] = mtf_rows_to_dataframe(scans)
                st.session_state["last_mtf_scans"] = scans
            except Exception as e:
                st.error(f"Scan failed: {e}")
                st.stop()

    df = st.session_state.get("last_mtf_df")
    scans = st.session_state.get("last_mtf_scans", [])
    if df is None or df.empty:
        st.warning("Click **Scan now** to load multi-timeframe signals.")
        st.stop()

    trade_ok = len(df[df["Trade OK"] == "✅"])
    premium = len(df[df["MTF strength"].isin(["PREMIUM", "VERY_STRONG"])])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Scanned", len(df))
    c2.metric("Checklist passed", trade_ok)
    c3.metric("STRONG+ MTF", premium)
    c4.metric("Bear / Bull", f"{len(df[df['MTF score'] < -30])} / {len(df[df['MTF score'] > 30])}")

    st.plotly_chart(make_mtf_strength_heatmap(df), use_container_width=True)
    st.plotly_chart(make_mtf_score_bar(df), use_container_width=True)
    st.plotly_chart(make_rsi_mtf_heatmap(df), use_container_width=True)

    st.subheader("Checklist & detail")
    show_cols = [
        "Instrument",
        "Direction",
        "MTF badge",
        "MTF strength",
        "MTF score",
        "Headline",
        "Checklist",
        "Trade OK",
        "Check summary",
        "M15 signal",
        "H1 signal",
        "H4 signal",
        "D1 signal",
    ]
    st.dataframe(df[[c for c in show_cols if c in df.columns]], use_container_width=True, hide_index=True)

    with st.expander("Checklist breakdown (per instrument)"):
        for s in scans:
            if not s.checklist:
                continue
            st.markdown(f"**{s.display_name}** — {s.checklist.summary}")
            for item in s.checklist.items:
                icon = "✅" if item.passed else "⬜"
                st.write(f"{icon} {item.label}: {item.detail}")

    with st.expander("Strength legend"):
        st.markdown(
            """
| Tier | Meaning |
|------|---------|
| **PREMIUM ★★★** | Emerald or Ruby GEM |
| **VERY_STRONG ★★** | Confirmed entry |
| **STRONG ★** | 3rd divergence setup |
| **MEDIUM ◆** | Raw divergence |
| **WEAK ·** | OB/OS only |

**Checklist (6):** clear signal · execution · S/R location · RSI zone · risk plan · 2+ TFs agree  
**Trade OK** = ≥4/6 checks and STRONG or better.
            """
        )


if __name__ == "__main__":
    main()
