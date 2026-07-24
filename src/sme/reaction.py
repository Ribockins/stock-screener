"""Measure price reaction after a signal (RQS + SFM labels)."""

from __future__ import annotations

import pandas as pd

from src.sme.detect import _atr
from src.sme.models import ReactionOutcome, SignalEvent


def measure_reaction(
    df: pd.DataFrame,
    event: SignalEvent,
    window: int,
    *,
    weak_mfe_atr: float = 0.35,
    good_mfe_atr: float = 1.0,
) -> ReactionOutcome:
    """MFE/MAE in ATR units over bars after signal."""
    out = df.copy()
    out.columns = [str(c).lower() for c in out.columns]
    n = len(out)
    i = event.bar_index
    end = min(n - 1, i + window)
    if end <= i:
        return ReactionOutcome(0.0, 0.0, "WEAK", 0)

    atr_s = _atr(out, 14)
    atr_i = float(atr_s.iloc[i]) if not pd.isna(atr_s.iloc[i]) and atr_s.iloc[i] > 0 else float(out["close"].iloc[i]) * 0.01
    entry = float(out["close"].iloc[i])
    future = out.iloc[i + 1 : end + 1]

    if event.direction == "BEARISH":
        mfe = (entry - future["low"].min()) / atr_i
        mae = (future["high"].max() - entry) / atr_i
        invalidated = float(out["high"].iloc[end]) > entry + 0.3 * atr_i and mfe < weak_mfe_atr
    else:
        mfe = (future["high"].max() - entry) / atr_i
        mae = (entry - future["low"].min()) / atr_i
        invalidated = float(out["low"].iloc[end]) < entry - 0.3 * atr_i and mfe < weak_mfe_atr

    mfe = max(0.0, float(mfe))
    mae = max(0.0, float(mae))

    if invalidated and mae > 0.5:
        quality, rqs = "INVALIDATED", -4
    elif mfe >= good_mfe_atr and mae < 0.5:
        quality, rqs = "STRONG", 4
    elif mfe >= weak_mfe_atr:
        quality, rqs = "OK", 2
    elif mfe > 0.1:
        quality, rqs = "WEAK", 1
    else:
        quality, rqs = "FAILURE", 0

    if mae > 1.0 and mfe < weak_mfe_atr:
        quality, rqs = "FAILURE", -2

    return ReactionOutcome(mfe, mae, quality, rqs)
