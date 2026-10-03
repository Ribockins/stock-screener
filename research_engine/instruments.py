"""NG and WTI are the active universe. Prices are Yahoo continuous front months."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Instrument:
    symbol: str
    yahoo: str
    point_size: Decimal
    flat_band: Decimal
    timezone: str
    profile: str
    contract_note: str


INSTRUMENTS = {
    "NG": Instrument(
        symbol="NG",
        yahoo="NG=F",
        point_size=Decimal("0.001"),
        flat_band=Decimal("1"),
        timezone="America/New_York",
        profile="energy",
        contract_note="Yahoo NG=F — непрерывный фронт Henry Hub, без поправки на rollover. Шаг цены 0.001.",
    ),
    "WTI": Instrument(
        symbol="WTI",
        yahoo="CL=F",
        point_size=Decimal("0.01"),
        flat_band=Decimal("1"),
        timezone="America/New_York",
        profile="energy",
        contract_note="Yahoo CL=F — непрерывный фронт WTI, без поправки на rollover. Шаг цены 0.01.",
    ),
}

ACTIVE = ("NG", "WTI")


def instrument(symbol: str) -> Instrument | None:
    return INSTRUMENTS.get(symbol)
