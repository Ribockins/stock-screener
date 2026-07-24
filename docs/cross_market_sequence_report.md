# Cross-market sequence report

_Regenerate: `python scripts/cross_market_profile_batch.py` → also writes `reports/cross_market_sequence_report.md` (gitignored)._

_Sierra uploads · peak hours local TZ · 30m fade retrace @ anchors_

## Data quality (latest)

| Symbol | Bar | Days | Calendar | Peak hours |
|--------|-----|------|----------|------------|
| **FRA40** | 1m | 21 | Jun–Jul 2026 | 15:00, 14:00, 16:00 |
| **UK100** | 1m | 21 | Jun–Jul 2026 | 14:00, 15:00, 16:00 |
| **US30 / SPX500** | 1m | 27 | Jun–Jul 2026 | 14:00–16:00 |
| **NGAS** | 5m | 27 | Jun–Jul 2026 | 14:00, 13:00 |
| **XAUUSD** | 1m | 27 | Jun–Jul 2026 | 14:00, 15:00, 02:00 |
| **GER30 / EUSTX50 / ESP35** | H1/1m | 22 | Jan–Feb 2026 | EU afternoon |

**Still missing:** VOLX 1m, USOil 1m, CORNF/DJFXJPY re-upload.

**Daily macro:** `docs/cross_market_daily_report.md` · `config/macro_bias.json`

## Anchor retrace — FRA40 & UK100 (1m, Jun–Jul 2026)

| Symbol | Anchor | Med retrace | ≥50% | GEM note |
|--------|--------|-------------|------|----------|
| **FRA40** | **11:00** | **66.7%** | 52% | Primary EU morning fade |
| **FRA40** | **17:30** | **71.7%** | 57% | US overlap — best CAC window |
| FRA40 | 15:30 | 32.0% | 48% | Skip blind fade |
| **UK100** | **11:00** | **52.8%** | 52% | FTSE morning fade |
| UK100 | 15:30 | 38.5% | 48% | Weak |
| UK100 | 17:30 | 24.4% | 38% | Avoid |

## Lead–lag (15m, same calendar where possible)

| Pair | Lag | Corr | Read |
|------|-----|------|------|
| **UK100→FRA40** | FRA40 ~60m ahead | 0.52 | Watch CAC for UK direction |
| UK100→US30 | US30 ~60m ahead | 0.10 | Weak — use for NY handoff only |
| US30→SPX500 | sync | 0.72 | US cluster |
| NGAS→US30 | US30 ~45m ahead | 0.03 | NGAS not a US leader |

## Sequence (GEM + VECTOR)

1. **London 11:00** — UK100 fade; confirm with FRA40 (CAC often leads UK by ~1h on 15m).
2. **Paris 17:30** — FRA40 fade (strongest CAC anchor in sample).
3. **NY 14:30** — US30/SPX500/NGAS shared peak (1m/5m execution).
4. **Macro filter** — yesterday US30 ≤−1% → gold/EU mild long bias (`macro_bias.json`).
5. **GEM CONFIRMED** + **VECTOR** to profile `exit_et`.
