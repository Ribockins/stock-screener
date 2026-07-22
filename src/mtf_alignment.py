"""
Brian Shannon MTF alignment — read M15/H1/H4/D together.

See docs/books/15-shannon-multiple-timeframes.md
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from src.gem_platform import InstrumentMTFScan
from src.gem_strength import STRENGTH_RANK


@dataclass
class MTFAlignment:
    symbol: str
    display_name: str
    read: str  # one-line Shannon interpretation
    aligned: bool
    direction: str  # BULLISH | BEARISH | MIXED
    strength: str  # weak | moderate | strong | regime


def _dir(scan: InstrumentMTFScan, tf: str) -> str:
    r = scan.ratings.get(tf)
    if not r or r.strength == "NONE" or r.direction == "NEUTRAL":
        return "NEUTRAL"
    return r.direction


def _strong(scan: InstrumentMTFScan, tf: str) -> bool:
    r = scan.ratings.get(tf)
    if not r:
        return False
    return STRENGTH_RANK.get(r.strength, 0) >= STRENGTH_RANK["STRONG"]


def interpret_shannon(scan: InstrumentMTFScan) -> MTFAlignment:
    d15 = _dir(scan, "15")
    d1h = _dir(scan, "60")
    d4h = _dir(scan, "240")
    d1d = _dir(scan, "1d")

    s15 = _strong(scan, "15")
    s1h = _strong(scan, "60")
    s4h = _strong(scan, "240")
    s1d = _strong(scan, "1d")

    name = scan.display_name

    # M15 strong opposite H1/H4 bull
    if s15 and d15 == "BEARISH" and d1h == "BULLISH" and d4h == "BULLISH":
        return MTFAlignment(
            scan.symbol, name,
            "M15 bear vs H1/H4 bull — likely short-term pullback",
            False, "MIXED", "weak",
        )
    if s15 and d15 == "BULLISH" and d1h == "BEARISH" and d4h == "BEARISH":
        return MTFAlignment(
            scan.symbol, name,
            "M15 bull vs H1/H4 bear — likely short-term bounce",
            False, "MIXED", "weak",
        )

    # H1 + H4 aligned bear/bull
    if s1h and s4h and d1h == d4h and d1h in ("BULLISH", "BEARISH"):
        dr = d1h.lower()
        if s1d and d1d == d1h:
            return MTFAlignment(
                scan.symbol, name,
                f"D1+H4+H1 {dr} — possible regime shift",
                True, d1h, "regime",
            )
        return MTFAlignment(
            scan.symbol, name,
            f"H1+H4 {dr} — strong swing warning",
            True, d1h, "strong",
        )

    # H1 strong, H4 neutral
    if s1h and d4h == "NEUTRAL":
        return MTFAlignment(
            scan.symbol, name,
            f"H1 {d1h.lower()} candidate — H4 not confirming yet",
            False, d1h if d1h != "NEUTRAL" else "MIXED", "moderate",
        )

  # H4 + D resistance context (bear on H4 with strong H4)
    if s4h and d4h == "BEARISH" and s1d:
        return MTFAlignment(
            scan.symbol, name,
            "H4 bear + D1 active — premium swing candidate",
            True, "BEARISH", "strong",
        )

    if s1h:
        return MTFAlignment(
            scan.symbol, name,
            f"H1 {d1h.lower()} — check H4/D before full size",
            d1h == d4h, d1h if d1h != "NEUTRAL" else "MIXED", "moderate",
        )

    return MTFAlignment(
        scan.symbol, name,
        "No strong MTF alignment — monitor",
        False, "MIXED", "weak",
    )


def alignment_for_scans(scans: List[InstrumentMTFScan]) -> List[MTFAlignment]:
    return [interpret_shannon(s) for s in scans]
