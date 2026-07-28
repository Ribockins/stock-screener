"""WARNING vs CONFIRMED vs WAIT — Douglas: signal is not necessarily a trade."""

from __future__ import annotations

from src.gem.models import GEMAnalysis
from src.gem_strength import GemStrengthRating, STRENGTH_RANK
from src.scan_checklist import ScanChecklist

TIER_WAIT = "WAIT"
TIER_WARNING = "WARNING"
TIER_CONFIRMED = "CONFIRMED"


def execution_tier(
    analysis: GEMAnalysis | None,
    rating: GemStrengthRating | None,
    checklist: ScanChecklist | None = None,
) -> str:
    """
    WAIT — no actionable edge.
    WARNING — candidate (setup / ARMED); do not jump in on emotion.
    CONFIRMED — trade checklist passed or GEM/entry triggered.
    """
    if not analysis or not rating:
        return TIER_WAIT

    if checklist and checklist.trade_ok:
        return TIER_CONFIRMED

    if analysis.exec_state in ("TRIGGERED_LONG", "TRIGGERED_SHORT"):
        return TIER_CONFIRMED

    if analysis.buy_gem or analysis.sell_gem:
        if checklist and checklist.score >= 4:
            return TIER_CONFIRMED
        return TIER_WARNING

    if analysis.buy_entry or analysis.sell_entry:
        return TIER_CONFIRMED

    rank = STRENGTH_RANK.get(rating.strength, 0)
    if rank >= STRENGTH_RANK["STRONG"]:
        if analysis.exec_state in ("ARMED_LONG", "ARMED_SHORT"):
            return TIER_WARNING
        if analysis.buy_setup or analysis.sell_setup:
            return TIER_WARNING

    return TIER_WAIT


def tier_label(tier: str) -> str:
    return {
        TIER_CONFIRMED: "CONFIRMED",
        TIER_WARNING: "WARNING",
        TIER_WAIT: "WAIT",
    }.get(tier, tier)
