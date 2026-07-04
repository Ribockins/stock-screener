"""Map GEM strength tier to EDGE score 0–4 (Disciplined Trader scale)."""

from src.gem_strength import STRENGTH_RANK

STRENGTH_TO_EDGE_SCORE = {
    "NONE": 0,
    "WEAK": 1,
    "MEDIUM": 2,
    "STRONG": 3,
    "VERY_STRONG": 3,
    "PREMIUM": 4,
}


def edge_score_from_strength(strength: str) -> int:
    return STRENGTH_TO_EDGE_SCORE.get(strength, 0)
