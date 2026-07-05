# EDGE 2.9 — Native Hybrid Engine

Python port of your TradingView Pine script **EDGE2.9 • NATIVE HYBRID ENGINE • LIGHT**.

## Mapping Pine → Python

| Pine | Python |
|------|--------|
| `f_engine()` | `src/edge_native.py` → `analyze_native_engine()` |
| `f_side_score()` | `side_score()` |
| MTF `request.security` table | `GEMPlatform.scan_watchlist_mtf()` → `native_signals` per TF |
| Super alignment (M5…D) | `super_alignment()` on scanned TFs |
| Score 0–4 | `NativeEngineResult.score` / `score_dir` |
| RSI+MFI div memory | `rsi_*_memory`, `mfi_*_memory` |
| Zone 80 / 15% | `config/edge_native_29.json` → `zone` |
| Price reaction | wick / engulf / close-back-inside |

## Native score (0–4)

| Score | Meaning (Pine) |
|-------|----------------|
| 0 | No active divergence memory |
| 1 | RSI **or** MFI divergence in memory |
| 2 | RSI **and** MFI divergence in memory |
| 3 | Score 2+ **and** near support (buy) / resistance (sell) |
| 4 | Score 3+ **and** price reaction candle |

**Not the same** as GEM strength (PREMIUM / STRONG) or legacy `edge_score_from_strength()`.

## Config

`config/edge_native_29.json` — defaults match your Pine inputs:

- RSI 14, OB 72, OS 28  
- MFI 14, OB 80, OS 20  
- Lookback 84, extreme memory 10, divergence memory 5  
- Zone lookback 80, width 15%  
- Reaction wick 0.45, close strength 0.55  

## GEM My List

Notes column now includes e.g. `EDGE2.9 NAT4↑`, `SUPER ALIGN BUY` when all scanned TFs align.

## Pair trading (A10/B12)

Synthetic index spread channel is separate — see `src/pair_indices.py` and `reports/a10_b12_spread_chart.png`.

## Pine reference

Full TradingView source: paste stored in project history; stub header in `pine/edge_2_9_native_hybrid.pine`.

## Tests

```bash
PYTHONPATH=/workspace pytest tests/test_edge_native.py -v
```
