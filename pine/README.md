# GEM Logic 1.5 (Pine Script)

Reference indicator: **GEM Logic 1.5** (`//@version=6`).

The canonical Pine source is maintained in this repo as the Python port baseline. If you paste an updated script from TradingView, replace `gem_logic_1_5.pine` and update `src/gem/dashboard.py` / `src/gem/analyzer.py` to match.

## Python port map

| Pine | Python |
|------|--------|
| `f_local_tf_pack()` | `src/gem/dashboard.py` → `compute_tf_dashboard()` |
| RSI divergence memory | `src/gem/analyzer.py` |
| MFI divergence (dashboard) | `src/gem/dashboard.py` (valuewhen-style) |
| Candle combinations | `src/gem/candles.py` |
| Universal GEM | `analyzer._gem_confluence()` + dashboard GM column |
| MTF table (15/H1/H4/D) | `gem_platform.scan_watchlist_mtf()` + `gem_my_list.render_terminal_matrix_markdown()` |
| EDGE RSI+MFI combo | `src/edge_engine.py` |

## Dashboard columns

- **R1** — RSI zone (OS/OB)
- **R2/R3** — RSI cycle tiers (exit OS/OB → cross 50 → re-enter)
- **D1/D2/D3** — divergence events tagged to cycle tier
- **MF** — MFI zone
- **MV** — MFI divergence direction
- **CDL** — bullish/bearish candle combo
- **GM** — universal GEM edge (OS/OB + div + candle within window)
- **Score** — 0–11 (D3 counts double)

See `docs/gem-logic-1.5.md` for full parameter defaults.
