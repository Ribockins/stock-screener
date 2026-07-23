"""SME data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SignalEvent:
    bar_index: int
    direction: str  # BULLISH | BEARISH
    signal_type: str
    price: float
    rsi: float
    zone_key: float


@dataclass
class ReactionOutcome:
    mfe_atr: float
    mae_atr: float
    quality: str  # STRONG | OK | WEAK | FAILURE | INVALIDATED
    rqs: int  # -4 .. +4


@dataclass
class SMELiveScore:
    spc: int = 0
    sfm_active: bool = False
    sfm_label: str = ""
    sse_active: bool = False
    sse_boost: int = 0
    rqs_last: Optional[int] = None
    sme_boost: int = 0
    svi_weight: int = 0
    edge_plus: int = 0
    src_summary: str = ""
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "spc": self.spc,
            "sfm_active": self.sfm_active,
            "sfm_label": self.sfm_label,
            "sse_active": self.sse_active,
            "sse_boost": self.sse_boost,
            "rqs_last": self.rqs_last,
            "sme_boost": self.sme_boost,
            "svi_weight": self.svi_weight,
            "edge_plus": self.edge_plus,
            "src_summary": self.src_summary,
            "tags": self.tags,
        }

    def cell_short(self) -> str:
        parts = []
        if self.sse_active:
            parts.append("SSE")
        if self.spc >= 2:
            parts.append(f"SPC{self.spc}")
        elif self.spc == 1:
            parts.append("SPC1")
        if self.sfm_active and self.sfm_label:
            parts.append(self.sfm_label[:4].upper())
        return "·".join(parts) if parts else "—"
