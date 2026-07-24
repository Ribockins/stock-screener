# Cross-market sequence report

_Regenerate: `python scripts/cross_market_profile_batch.py` → also writes `reports/cross_market_sequence_report.md` (gitignored)._

_Sierra uploads · peak hours local TZ · 30m fade retrace @ anchors_

## Data quality

| Symbol | Bar | Days | Range | Peak hours (local) |
|--------|-----|------|-------|-------------------|
| **NAS100** | 60m | 27 | 2026-06-23…2026-07-23 | 15:00, 14:00, 16:00, 20:00 |
| **GER30** | 60m | 22 | 2026-01-05…2026-02-03 | 14:00, 15:00, 07:00, 08:00 |
| **EUSTX50** | 1m | 22 | 2026-01-05…2026-02-03 | 15:00, 14:00, 19:00, 17:00 |
| **ESP35** | 1m | 22 | 2026-01-05…2026-02-03 | 15:00, 14:00, 16:00, 13:00 |
| **US30** | 1m | 27 | 2026-06-23…2026-07-23 | 15:00, 14:00, 16:00, 20:00 |
| **SPX500** | 1m | 27 | 2026-06-23…2026-07-23 | 15:00, 14:00, 16:00, 20:00 |
| **NGAS** | 5m | 27 | 2026-06-23…2026-07-23 | 14:00, 13:00, 15:00, 19:00 |

**Missing/empty:** CORNF, DJFXJPY (upload failed). **VOLX** still needed for intraday chain.

**Daily macro (2014–2026):** FRA40, UK100, US30, USOil, UKOil, XAUUSD, XAGUSD, NGAS — see `docs/cross_market_daily_report.md` + `config/macro_bias.json`.

**Note:** NAS100 & GER30 files are **~1h bars**, not 1m — use US30/SPX500/EUSTX50/ESP35 1m for execution.

**Calendar:** EU set (GER30/EUSTX50/ESP35) is **Jan–Feb 2026**; US set (NAS100/US30/SPX500/NGAS) is **Jun–Jul 2026** — cross-region lead-lag pairs are not comparable until exports share the same dates.

## Anchor retrace (fade, ~30m, median %)

| Symbol | Anchor | n | Med retrace | ≥50% |
|--------|--------|---|-------------|------|
| NAS100 | 14:30 | 21 | 73.7% | 67.0% |
| GER30 | 17:30 | 21 | 60.0% | 62.0% |
| EUSTX50 | 15:30 | 22 | 85.1% | 55.0% |
| ESP35 | 15:30 | 22 | 54.9% | 50.0% |
| US30 | 14:30 | 21 | 64.6% | 57.0% |
| SPX500 | 14:30 | 21 | 70.6% | 62.0% |
| NGAS | 14:30 | 22 | 50.0% | 50.0% |

## Lead–lag (15m returns)

| Pair | Lag (min) | Corr | Read |
|------|-----------|------|------|
| US30→SPX500 | 0 | 0.723 | synchronous |
| EUSTX50→ESP35 | 0 | 0.669 | synchronous |
| NGAS→US30 | -45 | 0.033 | US30 leads ~45m (weak) |

## Sequence (GEM + VECTOR)

1. **EU 15:30** — EUSTX50 / ESP35 fade; GER30 H1 context at 17:30 overlap.
2. **US 14:30** — NAS100 + US30 + SPX500 + NGAS shared peak; execute on 1m/5m legs.
3. **GEM** — CONFIRMED only inside active TEMPORAL row.
4. **VECTOR** — hold to `exit_et` / profile SL.
