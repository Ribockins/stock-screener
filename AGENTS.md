# AGENTS.md

## Cursor Cloud — Option C (cloud-only, no local PC)

Users on **Option C** do not run `install.bat` or `gem_app.py` on their computer. All GEM Logic scans run in **this Cloud VM**.

### On each Cloud Agent session (automatic layer)

The VM **update script** refreshes `.venv`, installs platform deps, and `tvdatafeed` shim.

### Run a scan for the user

```bash
cd /workspace && source .venv/bin/activate
python scripts/cloud_gem_report.py  # 4 TFs: 15m, 1h, 4h, daily + strength + checklist
```

Read **`reports/latest_gem_report.md`** (colour-coded 🟢 Emerald / 🔴 Ruby / ⚪ neutral + hex tags, MTF strength, **GEM Terminal Matrix**, checklist) and summarize actionable signals.

**GEM Logic 1.5 dashboard** (Pine `f_local_tf_pack` port): columns R1–R3, D1–D3, MF, MV, CDL, GM, Score 0–11 per TF — see `docs/gem-logic-1.5.md` and `src/gem/dashboard.py`.

### Finviz Top Gainers (separate list)

- Config: **`config/finviz_gainers.json`** (not mixed with main watchlist)
- Rank top 10 by market cap + bullish GEM only:

```bash
cd /workspace && source .venv/bin/activate
python scripts/finviz_top_cap_gem.py
```

Read **`reports/finviz_top_cap_gem.md`**.

### Watchlist

Edit **`config/watchlist.json`** when the user asks to add/remove symbols.

### Optional background monitor

```bash
SESSION_NAME="gem-cloud-monitor"
tmux -f /exec-daemon/tmux.portal.conf new-session -d -s "$SESSION_NAME" -c /workspace -- \
  bash -lc './scripts/cloud_monitor_loop.sh'
```

Default refresh: **5 minutes** (`GEM_REFRESH_MINUTES` env).


### GEM My List (compact trade board)

User phrase: **"GEM my list"** (also: **gemlist**, **my list**, **scan**).

Shows: `Instrument | Checklist | MTF | Notes` — trade-ready first, then full watchlist.

```bash
cd /workspace && source .venv/bin/activate
python scripts/gem_my_list.py
```

Same as `cloud_gem_report.py`; report title starts with **GEM My List**.

Also includes **4 separate score tables**: M15 → H1 → H4 → Daily (all instruments each).
User may say: **"GEM 4 tables"** or **"scores by timeframe"**.

### User-facing phrases

- **"GEM my list"** / **"gemlist"** / **"scan my instruments"** → `gem_my_list.py` or `cloud_gem_report.py`
- "Add TSLA" → edit `config/watchlist.json`
- They do **not** need local install steps

### Strategy library (100 books → EDGE)

Konспект по названиям: **`docs/edge-reading-library.md`** (топ-15, MTF, VPA, чеклист).

### GEM engine

- Code: `src/gem/` + `src/gem_platform.py`
- Defaults: RSI 14, OS 28, OB 72, 3 divergence events, 8-bar GEM window

### Data

TradingView (limited nologin) → yfinance fallback. Requires network.

### Legacy

- Old screener: `scripts/run_screener.py`
- Desktop GUI: `gem_app.py` (needs display; not used for Option C)

### EDGE layer (RSI + MFI + volume)

- Code: `src/edge_combos.py` (MFI + RSI/MFI divergence), `src/volume_signals.py`, `src/edge_engine.py`
- Wired into MTF scan: `GEMPlatform.scan_watchlist_mtf()` fills `InstrumentMTFScan.edge_signals` per TF
- Reports: **EDGE (H1)** column on GEM My List; per-TF tables show **MFI** and **Edge** (0–4)
- Tests: `PYTHONPATH=/workspace pytest tests/test_edge_signals.py -v`

### Full scan pipeline (recommended)

```bash
cd /workspace && source .venv/bin/activate
PYTHONPATH=/workspace python scripts/gem_scan_pipeline.py
```

Does in one pass: **live MTF scan** → `data/signal_journal.csv` → `data/signal_ledger.csv` → `reports/latest_gem_report.md`.

CSV data stays on the machine (see `data/.gitignore`); code/config is on GitHub.
