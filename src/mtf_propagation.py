"""
MTF Propagation Layer — score whether a lower-TF signal may develop on H1/H4/D1.

See docs/edge-mtf-propagation.md
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.edge_combos import ComboSignal
from src.gem_platform import InstrumentMTFScan

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "mtf_propagation.json"


@dataclass
class PropagationResult:
    score: int
    band: str  # local | watch | expansion
    label: str
    factors: list[str]


def _load_weights() -> dict:
    if CONFIG.exists():
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    return {"weights": {}, "bands": {"local_noise_max": 3, "watch_max": 6, "expansion_min": 7}}


def score_instrument_scan(
    scan: InstrumentMTFScan,
    combo_m15: Optional[ComboSignal] = None,
) -> PropagationResult:
    """
    Heuristic propagation score from existing GEM MTF + optional M15 RSI/MFI combo.
    OBV/CVD/VP — placeholders until feeds exist (weight applied when flags added).
    """
    cfg = _load_weights()
    w = cfg.get("weights", {})
    bands = cfg.get("bands", {})
    score = 0
    factors: list[str] = []

    r15 = scan.ratings.get("15")
    r60 = scan.ratings.get("60")
    r240 = scan.ratings.get("240")
    a15 = scan.analyses.get("15")
    a60 = scan.analyses.get("60")

    if combo_m15:
        if combo_m15.rsi_bear_div or combo_m15.rsi_bull_div:
            score += int(w.get("rsi_div_m15", 1))
            factors.append("M15 RSI div")
        if combo_m15.mfi_bear_div or combo_m15.mfi_bull_div:
            score += int(w.get("mfi_div_m15", 2))
            factors.append("M15 MFI div")
        if combo_m15.dual_bear_div or combo_m15.dual_bull_div:
            factors.append("M15 DUAL div")
        if combo_m15.money_confirms_weakness:
            score += 1
            factors.append("price↑ MFI↓")

    if a15 and (a15.near_support or a15.near_resistance):
        score += int(w.get("at_higher_tf_level", 2))
        factors.append("M15 at S/R zone")

    # H1 alignment: same direction weakness on H1
    if r15 and r60 and r15.direction == r60.direction and r15.direction != "NEUTRAL":
        if r60.strength in ("STRONG", "VERY_STRONG", "PREMIUM"):
            score += int(w.get("h1_weakness_align", 2))
            factors.append("H1 aligns")

    if r240 and r240.strength in ("STRONG", "VERY_STRONG", "PREMIUM"):
        score += int(w.get("h4_overstretched", 2))
        factors.append("H4 stretched")

    if a60 and a60.in_overbought and (combo_m15 and combo_m15.mfi_bear_div):
        score += 1
        factors.append("H1 OB + M15 MFI div")

    local_max = int(bands.get("local_noise_max", 3))
    watch_max = int(bands.get("watch_max", 6))
    exp_min = int(bands.get("expansion_min", 7))

    if score >= exp_min:
        band, label = "expansion", "MTF expansion potential"
    elif score > watch_max:
        band, label = "watch_high", "Elevated MTF carry"
    elif score > local_max:
        band, label = "watch", "Weak MTF carry"
    else:
        band, label = "local", "M15-local only"

    return PropagationResult(score=score, band=band, label=label, factors=factors)
