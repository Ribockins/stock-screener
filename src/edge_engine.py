"""EDGE engine — RSI + MFI divergences and volume on each GEM timeframe bar."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from src.edge_combos import ComboSignal, analyze_rsi_mfi, calculate_mfi
from src.gem.rsi import calculate_rsi
from src.volume_signals import VolumeSignals, analyze_volume


@dataclass
class EdgeBarSignals:
    """Per-timeframe EDGE read (RSI+MFI combo + volume)."""

    mfi: float
    relative_volume: float
    volume_divergence: bool
    volume_exhaustion: bool
    rsi_bear_div: bool
    rsi_bull_div: bool
    mfi_bear_div: bool
    mfi_bull_div: bool
    dual_bear_div: bool
    dual_bull_div: bool
    money_confirms_weakness: bool
    edge_combo_score: int  # 0–4
    summary: str

    def to_dict(self) -> dict:
        return {
            "mfi": self.mfi,
            "relative_volume": self.relative_volume,
            "volume_divergence": self.volume_divergence,
            "volume_exhaustion": self.volume_exhaustion,
            "rsi_bear_div": self.rsi_bear_div,
            "rsi_bull_div": self.rsi_bull_div,
            "mfi_bear_div": self.mfi_bear_div,
            "mfi_bull_div": self.mfi_bull_div,
            "dual_bear_div": self.dual_bear_div,
            "dual_bull_div": self.dual_bull_div,
            "money_confirms_weakness": self.money_confirms_weakness,
            "edge_combo_score": self.edge_combo_score,
            "summary": self.summary,
        }


def edge_combo_score(combo: ComboSignal, volume: VolumeSignals) -> int:
    """0–4: RSI div, MFI div, dual div, volume confirmation."""
    score = 0
    if combo.rsi_bear_div or combo.rsi_bull_div:
        score += 1
    if combo.mfi_bear_div or combo.mfi_bull_div:
        score += 1
    if combo.dual_bear_div or combo.dual_bull_div:
        score += 1
    if (
        volume.relative_volume >= 1.25
        or volume.volume_divergence
        or volume.volume_exhaustion
        or combo.money_confirms_weakness
    ):
        score += 1
    return min(score, 4)


def analyze_edge_bar(
    df: pd.DataFrame,
    *,
    rsi_period: int = 14,
    mfi_period: int = 14,
    div_lookback: int = 10,
) -> Optional[EdgeBarSignals]:
    """Full EDGE pass on normalized OHLCV (last bar)."""
    if df is None or df.empty:
        return None

    out = df.copy()
    out.columns = [str(c).lower() for c in out.columns]
    for col in ("high", "low", "close", "volume"):
        if col not in out.columns:
            return None

    rsi = calculate_rsi(out["close"], rsi_period)
    combo = analyze_rsi_mfi(out, rsi, mfi_period=mfi_period, div_lookback=div_lookback)
    if combo is None:
        return None

    vol = analyze_volume(out)

    score = edge_combo_score(combo, vol)
    parts = [p for p in (combo.summary, vol.summary) if p and p != "volume neutral"]
    if score >= 3:
        parts.append(f"edge {score}/4")

    return EdgeBarSignals(
        mfi=combo.mfi,
        relative_volume=vol.relative_volume,
        volume_divergence=vol.volume_divergence,
        volume_exhaustion=vol.volume_exhaustion,
        rsi_bear_div=combo.rsi_bear_div,
        rsi_bull_div=combo.rsi_bull_div,
        mfi_bear_div=combo.mfi_bear_div,
        mfi_bull_div=combo.mfi_bull_div,
        dual_bear_div=combo.dual_bear_div,
        dual_bull_div=combo.dual_bull_div,
        money_confirms_weakness=combo.money_confirms_weakness,
        edge_combo_score=score,
        summary="; ".join(parts) if parts else "no edge",
    )


# Re-export for tests / indicators module consumers
__all__ = [
    "EdgeBarSignals",
    "analyze_edge_bar",
    "calculate_mfi",
    "edge_combo_score",
]
