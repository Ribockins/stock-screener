"""Tests for GEM report colour chips."""

from src.gem_colours import (
    bear_chip,
    bull_chip,
    checklist_chip,
    dashboard_cell,
    dashboard_score_cell,
    direction_chip,
    signal_chip,
    tier_chip,
)


def test_direction_chip():
    assert "🟢" in direction_chip("BULLISH")
    assert "#00c896" in direction_chip("BULLISH")
    assert "🔴" in direction_chip("BEARISH")
    assert "⚪" in direction_chip("NEUTRAL")


def test_dashboard_cells():
    assert "OS" in dashboard_cell("OS", 1, rsi_zone=True)
    assert "🟢" in dashboard_cell("B", 1)
    assert "🔴" in dashboard_cell("S", -1)
    assert "⚪" in dashboard_cell("0", 0)


def test_dashboard_score_bias():
    assert "🟢" in dashboard_score_cell(5, 1)
    assert "🔴" in dashboard_score_cell(5, -1)


def test_signal_and_tier():
    assert "EMERALD" in signal_chip("EMERALD GEM") or "🟢" in signal_chip("EMERALD GEM")
    assert "CONFIRMED" in tier_chip("CONFIRMED")
    assert "WARNING" in tier_chip("WARNING")


def test_checklist_chip():
    assert "✅" in checklist_chip(6, True)
    assert "⚠️" in checklist_chip(4, False)
