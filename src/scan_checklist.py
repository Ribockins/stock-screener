"""Pre-trade checklist derived from GEM scan (per symbol, per TF + combined)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from src.gem.models import GEMAnalysis
from src.gem_strength import GemStrengthRating, STRENGTH_RANK, rate_gem_analysis


@dataclass
class ChecklistItem:
    key: str
    label: str
    passed: bool
    detail: str


@dataclass
class ScanChecklist:
    symbol: str
    display_name: str
    timeframe: str
    items: List[ChecklistItem] = field(default_factory=list)
    score: int = 0  # 0–6
    trade_ok: bool = False
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "display_name": self.display_name,
            "timeframe": self.timeframe,
            "score": self.score,
            "trade_ok": self.trade_ok,
            "summary": self.summary,
            "items": [
                {"key": i.key, "label": i.label, "passed": i.passed, "detail": i.detail}
                for i in self.items
            ],
        }


def build_checklist(
    analysis: GEMAnalysis,
    rating: GemStrengthRating,
    display_name: str,
    timeframe: str,
    mtf_ratings: Optional[List[GemStrengthRating]] = None,
) -> ScanChecklist:
    """Six-point checklist from strategy rules discussed with user."""
    a = analysis
    items: List[ChecklistItem] = []

    # 1. Signal type
    sig_ok = rating.strength in ("STRONG", "VERY_STRONG", "PREMIUM")
    items.append(
        ChecklistItem(
            "signal",
            "Clear GEM signal (setup+ or GEM)",
            sig_ok,
            rating.signal_name if sig_ok else f"Low edge: {rating.signal_name}",
        )
    )

    # 2. Execution state
    exec_ok = a.exec_state in ("ARMED_LONG", "ARMED_SHORT", "TRIGGERED_LONG", "TRIGGERED_SHORT")
    if rating.direction == "BULLISH":
        exec_ok = exec_ok and a.exec_state in ("ARMED_LONG", "TRIGGERED_LONG")
    elif rating.direction == "BEARISH":
        exec_ok = exec_ok and a.exec_state in ("ARMED_SHORT", "TRIGGERED_SHORT")
    items.append(
        ChecklistItem(
            "execution",
            "Execution armed or triggered",
            exec_ok,
            a.exec_state,
        )
    )

    # 3. Location (S/R)
    loc_ok = False
    if rating.direction == "BULLISH":
        loc_ok = a.near_support
    elif rating.direction == "BEARISH":
        loc_ok = a.near_resistance
    items.append(
        ChecklistItem(
            "location",
            "Price at favourable S/R zone",
            loc_ok,
            "near support" if a.near_support else ("near resistance" if a.near_resistance else "mid-range"),
        )
    )

    # 4. RSI zone
    rsi_ok = False
    if rating.direction == "BULLISH":
        rsi_ok = a.in_oversold or a.rsi < 45
    elif rating.direction == "BEARISH":
        rsi_ok = a.in_overbought or a.rsi > 55
    else:
        rsi_ok = 40 <= a.rsi <= 60
    items.append(
        ChecklistItem(
            "rsi",
            "RSI supports direction",
            rsi_ok,
            f"RSI {a.rsi:.1f}",
        )
    )

    # 5. Risk (stops defined when triggered)
    risk_ok = a.exec_state.startswith("TRIGGERED") and a.stop_price is not None
    if rating.strength in ("VERY_STRONG", "PREMIUM") and not risk_ok:
        risk_ok = True  # GEM tier implies planned risk even if stop not simulated
    items.append(
        ChecklistItem(
            "risk",
            "Risk plan (stop/TP or premium tier)",
            risk_ok,
            f"stop={a.stop_price}" if a.stop_price else "use structure invalidation",
        )
    )

    # 6. MTF alignment
    mtf_ok = False
    mtf_detail = "single TF only"
    if mtf_ratings:
        same = [r for r in mtf_ratings if r.direction == rating.direction and r.direction != "NEUTRAL"]
        mtf_ok = len(same) >= 2
        mtf_detail = f"{len(same)}/4 TFs {rating.direction.lower()}"
    items.append(
        ChecklistItem(
            "mtf",
            "2+ timeframes agree",
            mtf_ok,
            mtf_detail,
        )
    )

    score = sum(1 for i in items if i.passed)
    trade_ok = score >= 4 and STRENGTH_RANK[rating.strength] >= STRENGTH_RANK["STRONG"]
    if score >= 5 and rating.strength in ("VERY_STRONG", "PREMIUM"):
        summary = "✅ Trade checklist passed"
    elif score >= 4:
        summary = "⚠️ Watch — partial checklist"
    else:
        summary = "⛔ No trade — wait"

    return ScanChecklist(
        symbol=a.symbol,
        display_name=display_name,
        timeframe=timeframe,
        items=items,
        score=score,
        trade_ok=trade_ok,
        summary=summary,
    )


def build_combined_checklist(
    symbol: str,
    display_name: str,
    per_tf: Dict[str, GEMAnalysis],
    per_tf_ratings: Dict[str, GemStrengthRating],
) -> ScanChecklist:
    """Use H1 as primary; MTF alignment from all four."""
    primary = per_tf.get("60") or next(iter(per_tf.values()), None)
    if not primary:
        return ScanChecklist(symbol, display_name, "MTF", [], 0, False, "No data")

    ratings = list(per_tf_ratings.values())
    rating = rate_gem_analysis(primary, "60")
    combined = build_checklist(primary, rating, display_name, "H1 (primary)", ratings)
    combined.timeframe = "MTF"
    return combined
