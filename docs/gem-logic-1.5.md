# GEM Logic 1.5 — Pine → Python

Upgraded GEM Logic 1.5 improves confluence by combining:

1. **RSI divergence memory** (3rd event in 84-bar lookback, OS 28 / OB 72)
2. **MFI zone + divergence** (20 / 80)
3. **Candlestick combinations** (engulfing, pin, stars, inside/outside, marubozu)
4. **Universal GEM** — recent OS/OB + divergence + candle within 8 bars
5. **RSI cycle engine** — R2/R3 and D1–D3 tiers for the terminal dashboard
6. **S/R range zones** with strength scoring (touches, div, candles, GEM, MTF OB/OS count)

## Defaults (Pine inputs = `GEMConfig`)

| Parameter | Default |
|-----------|---------|
| RSI length | 14 |
| Oversold / Overbought | 28 / 72 |
| Divergence lookback | 84 bars |
| Events required | 3 |
| MFI length | 14 |
| MFI OS / OB | 20 / 80 |
| GEM confirm window | 8 bars |
| Signal life | 4 bars |
| Stop buffer | 0.15% |
| TP1 / TP2 R:R | 1.0 / 2.0 |
| Range lookback | 50 |
| Zone size | 10% of range |

## Terminal dashboard score (0–11)

Per timeframe, Pine packs state into a single integer and displays:

`R1 | R2 | R3 | D1 | D2 | D3 | MF | MV | CDL | GM | Score`

Python: `src/gem/dashboard.py` — `TFDashboardState` / `compute_tf_dashboard()`.

**Score weights:** each active column +1, **D3 +2**, max 11.

**Bias:** GM direction if GEM fired; else sign of weighted sum (D3 ×2).

## Scan output

After `python3 scripts/gem_scan_pipeline.py`:

- **GEM My List** — trade board + reflection + **GEM Terminal Matrix** per instrument
- JSON: `reports/latest_gem_scan.json` → `terminal_matrix`

## R-cycle window (hours → bars)

| TF | Hours | Example bars |
|----|-------|----------------|
| M15 | 48 | 192 |
| H1 | 120 | 120 |
| H4 | 190 | 48 |
| D+ | 400 | scales by interval |

Implemented in `r_cycle_hours()` / `r_cycle_bars()` in `dashboard.py`.

## Differences vs legacy 0–4 `gem_score`

`GEMAnalysis.gem_score` remains a simple 0–4 chart-TF heuristic. Prefer **`dashboard_score`** (0–11) and the terminal matrix for MTF alignment — this matches TradingView GEM Logic 1.5.

## Pine source

Place the TradingView script at `pine/gem_logic_1_5.pine` when updating. The user-provided Logic 1.5 script is the reference for dashboard packing and cycle rules.
