"""Live SME score at current bar."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import pandas as pd

from src.gem.models import GEMAnalysis
from src.sme.detect import detect_signal_events
from src.sme.irp import svi_weight
from src.sme.models import SMELiveScore
from src.sme.reaction import measure_reaction

ROOT = Path(__file__).resolve().parents[2]
SME_CONFIG = ROOT / "config" / "sme.json"


def _load_config() -> dict:
    if SME_CONFIG.exists():
        return json.loads(SME_CONFIG.read_text(encoding="utf-8"))
    return {"enabled": True, "lookback_bars": 40}


def score_signal_memory(
    df: pd.DataFrame,
    current: GEMAnalysis,
    *,
    instrument_name: str,
    timeframe: str,
    edge_combo_score: int = 0,
) -> SMELiveScore:
    cfg = _load_config()
    if not cfg.get("enabled", True):
        return SMELiveScore(svi_weight=svi_weight(instrument_name))

    lookback = int(cfg.get("lookback_bars", 40))
    zone_mult = float(cfg.get("zone_atr_mult", 0.8))
    weak_atr = float(cfg.get("weak_mfe_atr", 0.35))
    good_atr = float(cfg.get("good_mfe_atr", 1.0))
    rw = cfg.get("reaction_window", {})
    window = int(rw.get(timeframe, rw.get("60", 12)))
    spc_map = cfg.get("spc_scores", {"1": 1, "2": 3, "3": 2, "4": 0})
    sse_cfg = cfg.get("sse_boost", {})
    max_sme = int(cfg.get("max_sme_boost", 8))
    max_svi = int(cfg.get("max_svi_weight", 10))

    cur_dir = None
    if current.sell_gem or current.sell_setup or current.raw_sell_div:
        cur_dir = "BEARISH"
    elif current.buy_gem or current.buy_setup or current.raw_buy_div:
        cur_dir = "BULLISH"

    score = SMELiveScore(svi_weight=max(-max_svi, min(max_svi, svi_weight(instrument_name))))

    if cur_dir is None or df is None:
        score.edge_plus = edge_combo_score + score.svi_weight
        score.src_summary = "no active signal"
        return score

    events = detect_signal_events(df, lookback=lookback, zone_atr_mult=zone_mult)
    same_dir = [e for e in events if e.direction == cur_dir]
    score.spc = min(4, len(same_dir)) if same_dir else 0

    spc_boost = int(spc_map.get(str(score.spc), spc_map.get(str(min(score.spc, 4)), 0)))

    # Reactions for completed events (not the current bar if it's the last event)
    n = len(df)
    reactions = []
    for ev in same_dir:
        if ev.bar_index >= n - 1:
            continue
        reactions.append(measure_reaction(df, ev, window, weak_mfe_atr=weak_atr, good_mfe_atr=good_atr))

    if reactions:
        last = reactions[-1]
        score.rqs_last = last.rqs
        if last.quality in ("WEAK", "FAILURE"):
            score.sfm_active = True
            score.sfm_label = last.quality.lower()
            score.tags.append(f"SFM:{score.sfm_label}")

    # SSE: second+ signal in zone after weak prior
    if len(same_dir) >= 2:
        prev_ev = same_dir[-2]
        cur_ev = same_dir[-1]
        zone_match = abs(cur_ev.zone_key - prev_ev.zone_key) <= 1
        prev_reaction = None
        if prev_ev.bar_index < n - 1:
            prev_reaction = measure_reaction(
                df, prev_ev, window, weak_mfe_atr=weak_atr, good_mfe_atr=good_atr
            )
        if zone_match and prev_reaction and prev_reaction.quality in (
            "WEAK",
            "FAILURE",
            "OK",
        ):
            score.sse_active = True
            score.sse_boost = int(sse_cfg.get("second_in_zone", 2))
            if abs(cur_ev.rsi - prev_ev.rsi) > 3:
                score.sse_boost += int(sse_cfg.get("stronger_than_first", 3)) - 2
            if current.buy_gem or current.sell_gem:
                score.sse_boost = max(score.sse_boost, int(sse_cfg.get("with_dual_or_gem", 4)))
            score.tags.append("SSE")

    score.sme_boost = min(max_sme, spc_boost + (score.sse_boost if score.sse_active else 0) + (2 if score.sfm_active else 0))
    score.edge_plus = edge_combo_score + score.sme_boost + score.svi_weight

    parts = []
    if score.sse_active:
        parts.append("SSE ON")
    if score.spc:
        parts.append(f"SPC {score.spc}")
    if score.sfm_active:
        parts.append(f"prior {score.sfm_label}")
    if score.rqs_last is not None:
        parts.append(f"last RQS {score.rqs_last:+d}")
    score.src_summary = "; ".join(parts) if parts else "pressure building" if score.spc == 1 else "—"

    return score
