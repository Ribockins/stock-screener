# Platform master playbook (one page)

## What you built

| Layer | Role | Repo |
|-------|------|------|
| **TEMPORAL** | When, how many points, fade/follow | `config/temporal_profiles/*.json` |
| **GEM** | Readiness: RSI, div, candle, score, exec state | `src/gem/`, `gem_my_list.py` |
| **EDGE** | Heat: combo 0–4, EDGE+, MFI, volume | `src/edge_engine.py`, heatmap in reports |
| **SME / SVI** | Memory + instrument priors | `src/sme/`, `config/irp_seed.json` |
| **VECTOR** | Hold vs exit (time + signal) | `execution_tier` + profile `exit_et` / SL |
| **APEX** | Pairs: spread z, lots US30/US500 1:7, UK/CAC 1:1.26 | `src/apex/`, `scripts/screen_apex_pairs.py` |

## Morning (60 seconds)

1. `python scripts/morning_command_center.py` → `reports/morning_command_center.md`
2. Run GEM scan (My List / cloud report) for symbols in **Active time windows**
3. Trade only where **TEMPORAL active** + **GEM ≥ WARNING** + **EDGE+ not cold**

## Entry rule (directional)

- **TEMPORAL** defines *side* (fade/follow), *clock*, *TP/SL in points*
- **GEM CONFIRMED** or checklist `trade_ok` required
- **Never** fade NGAS Friday 14:30 without fresh stats

## Exit rule (VECTOR)

- Primary: temporal `exit_et` or TP hit
- Fast: SL from profile (`beyond_extreme` + pad)
- Slow: GEM opposite trigger or MTF score collapse on hold TF

## APEX (parallel book)

- Only when pair screen / z-score says spread stretched
- Directional TEMPORAL on legs must not contradict spread mean reversion

## Data pipeline (finish the map)

For each symbol on your chart list:

1. Upload `5_min_*` or `1min_*` Sierra export
2. `python scripts/build_temporal_profile.py --symbol SYMBOL --input PATH` (when added)
3. Review JSON → merge into `config/temporal_profiles/`
4. Re-run morning command center

**Priority batch:** NGAS ✓ · US30 ✓ · SPX500 ✓ · NAS100 ✓ · GER30 ✓ · EUSTX50 ✓ · ESP35 ✓ · WTI · Brent · UK100 · VOLX · XAUUSD

## Cross-market batch

```bash
python scripts/cross_market_profile_batch.py
```

→ `reports/cross_market_sequence_report.md` + `cross_market_profiles.json` (anchors, weekday range, lead–lag on 15m returns).

Re-upload **1m** for NAS100/GER30 and align **date range** across EU+US before trusting VOLX→index chains.

## Daily macro layer

```bash
python scripts/cross_market_daily_batch.py
```

→ `docs/cross_market_daily_report.md` · `config/macro_bias.json` (US30 shock → gold/EU/NGAS next-day priors).

## Lead–lag (next research)

Same-calendar 1m/5m: VOLX shock → index lag minutes → oil/gold follow. NGAS↔US30 in current sample: US30 leads ~45m (weak corr).

## One screen (target UI)

Rows = instruments. Columns = TEMPORAL phase | EDGE heat | GEM Exec | VECTOR | APEX z.

Desktop: extend `desktop_app.py` or HTML dashboard like `open_reversal_dashboard.html`.
