"""GEM strategy signal strength — maps GEMAnalysis to graded strength tiers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from src.gem.models import GEMAnalysis

# Ordered weakest → strongest (for comparisons)
STRENGTH_RANK = {
    "NONE": 0,
    "WEAK": 1,
    "MEDIUM": 2,
    "STRONG": 3,
    "VERY_STRONG": 4,
    "PREMIUM": 5,
}


@dataclass
class GemStrengthRating:
    symbol: str
    timeframe: str
    direction: str  # BULLISH | BEARISH | NEUTRAL
    strength: str  # NONE … PREMIUM
    score: int  # signed -100 … +100
    signal_name: str
    confidence: float  # 0–1


def _signal_name(a: GEMAnalysis) -> str:
    if a.buy_gem:
        return "EMERALD GEM"
    if a.sell_gem:
        return "RUBY GEM"
    if a.buy_entry:
        return "LONG ENTRY"
    if a.sell_entry:
        return "SHORT ENTRY"
    if a.buy_setup:
        return "BUY SETUP"
    if a.sell_setup:
        return "SELL SETUP"
    if a.in_oversold:
        return "Oversold"
    if a.in_overbought:
        return "Overbought"
    return "—"


def rate_gem_analysis(analysis: GEMAnalysis, timeframe: str = "60") -> GemStrengthRating:
    """Rate a single bar's GEM output for heatmap and checklist."""
    a = analysis
    name = _signal_name(a)
    direction = "NEUTRAL"
    base = 0
    strength = "NONE"
    confidence = 0.15

    if a.buy_gem:
        direction, strength, base, confidence = "BULLISH", "PREMIUM", 95, 0.92
    elif a.sell_gem:
        direction, strength, base, confidence = "BEARISH", "PREMIUM", -95, 0.92
    elif a.buy_entry:
        direction, strength, base, confidence = "BULLISH", "VERY_STRONG", 78, 0.85
    elif a.sell_entry:
        direction, strength, base, confidence = "BEARISH", "VERY_STRONG", -78, 0.85
    elif a.buy_setup:
        direction, strength, base, confidence = "BULLISH", "STRONG", 58, 0.72
    elif a.sell_setup:
        direction, strength, base, confidence = "BEARISH", "STRONG", -58, 0.72
    elif a.raw_buy_div and a.divergence_state == "BUY":
        direction, strength, base, confidence = "BULLISH", "MEDIUM", 35, 0.55
    elif a.raw_sell_div and a.divergence_state == "SELL":
        direction, strength, base, confidence = "BEARISH", "MEDIUM", -35, 0.55
    elif a.in_oversold:
        direction, strength, base, confidence = "BULLISH", "WEAK", 18, 0.35
    elif a.in_overbought:
        direction, strength, base, confidence = "BEARISH", "WEAK", -18, 0.35

    # Execution + structure modifiers
    if a.exec_state == "ARMED_LONG" and direction == "BULLISH":
        base = min(100, base + 8)
        confidence = min(1.0, confidence + 0.06)
        if STRENGTH_RANK[strength] < STRENGTH_RANK["STRONG"]:
            strength = "STRONG"
    elif a.exec_state == "ARMED_SHORT" and direction == "BEARISH":
        base = max(-100, base - 8)
        confidence = min(1.0, confidence + 0.06)
        if STRENGTH_RANK[strength] < STRENGTH_RANK["STRONG"]:
            strength = "STRONG"
    elif a.exec_state in ("TRIGGERED_LONG", "TRIGGERED_SHORT"):
        confidence = min(1.0, confidence + 0.1)

    base += max(-12, min(12, a.gem_score * 3))
    if a.near_support and direction == "BULLISH":
        base += 5
        confidence += 0.04
    if a.near_resistance and direction == "BEARISH":
        base -= 5
        confidence += 0.04

    score = int(max(-100, min(100, base)))

    return GemStrengthRating(
        symbol=a.symbol,
        timeframe=timeframe,
        direction=direction,
        strength=strength,
        score=score,
        signal_name=name,
        confidence=round(min(1.0, confidence), 2),
    )


def combine_mtf_ratings(ratings: List[GemStrengthRating]) -> GemStrengthRating:
    """Aggregate per-TF ratings into one row for sorting / headline strength."""
    if not ratings:
        return GemStrengthRating("", "MTF", "NEUTRAL", "NONE", 0, "—", 0.0)

    sym = ratings[0].symbol
    bullish = [r for r in ratings if r.direction == "BULLISH" and r.strength != "NONE"]
    bearish = [r for r in ratings if r.direction == "BEARISH" and r.strength != "NONE"]

    def best(group: List[GemStrengthRating]) -> Optional[GemStrengthRating]:
        if not group:
            return None
        return max(group, key=lambda r: (STRENGTH_RANK[r.strength], abs(r.score)))

    b_best = best(bullish)
    s_best = best(bearish)
    align_b = len(bullish)
    align_s = len(bearish)

    if align_b >= 2 and (align_s < 2 or (b_best and s_best and STRENGTH_RANK[b_best.strength] >= STRENGTH_RANK[s_best.strength])):
        pick = b_best or bullish[0]
        strength = pick.strength
        if align_b >= 3 and STRENGTH_RANK[strength] >= STRENGTH_RANK["STRONG"]:
            strength = "PREMIUM" if strength in ("VERY_STRONG", "PREMIUM") else "VERY_STRONG"
        score = int(sum(r.score for r in bullish) / len(bullish))
        return GemStrengthRating(
            sym, "MTF", "BULLISH", strength, score, f"{pick.signal_name} ({align_b}/4 TF)", pick.confidence
        )

    if align_s >= 2:
        pick = s_best or bearish[0]
        strength = pick.strength
        if align_s >= 3 and STRENGTH_RANK[strength] >= STRENGTH_RANK["STRONG"]:
            strength = "PREMIUM" if strength in ("VERY_STRONG", "PREMIUM") else "VERY_STRONG"
        score = int(sum(r.score for r in bearish) / len(bearish))
        return GemStrengthRating(
            sym, "MTF", "BEARISH", strength, score, f"{pick.signal_name} ({align_s}/4 TF)", pick.confidence
        )

    pick = max(ratings, key=lambda r: abs(r.score))
    return GemStrengthRating(
        sym, "MTF", pick.direction, pick.strength, pick.score, pick.signal_name, pick.confidence
    )


def strength_badge(strength: str) -> str:
    icons = {
        "PREMIUM": "★★★",
        "VERY_STRONG": "★★",
        "STRONG": "★",
        "MEDIUM": "◆",
        "WEAK": "·",
        "NONE": "—",
    }
    return icons.get(strength, "—")
