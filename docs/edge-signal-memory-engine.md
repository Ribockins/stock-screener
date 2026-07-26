# SME — Signal Memory Engine

## Modules

| Code | Name | Role |
|------|------|------|
| **SFM** | Signal Failure Memory | Prior signal weak/failed — pressure may remain |
| **SSE** | Second Signal Effect | 2nd signal in zone after weak 1st — higher amplitude potential |
| **SPC** | Signal Pressure Count | Repeated same-direction GEM events in lookback |
| **RQS** | Reaction Quality Score | How price moved after prior signal (ATR-based) |
| **SVI** | Signal vs Instrument | Weight from `config/irp_seed.json` → later from ledger stats |
| **IRP** | Instrument Response Profile | Long-run behaviour per market (WTI/NG vs US500…) |

## EDGE+ formula (display)

```
EDGE+ = edge_combo (0–4) + sme_boost + svi_weight
```

## Data files (local / VM, not in Git by default)

| File | Content |
|------|---------|
| `data/signal_ledger.csv` | Every scan × instrument × TF (SME columns) |
| `data/signal_journal.csv` | H1 row per scan for discipline + your `result_r` |
| `reports/latest_gem_report.md` | Human GEM My List |

## Commands

```bash
python scripts/cloud_gem_report.py      # scan + report only
python scripts/signal_journal.py        # scan + journal only
python scripts/gem_scan_pipeline.py     # scan + journal + ledger + report (recommended)
```

## Roadmap

1. ✅ Live SME on scan (v1)
2. ✅ Ledger append per scan
3. ⏳ Outcome backfill job (MFE/MAE after N bars) → auto RQS
4. ⏳ SVI from ledger aggregates (replace seed weights)
5. ⏳ Pine labels: SSE / SPC on chart (optional)
