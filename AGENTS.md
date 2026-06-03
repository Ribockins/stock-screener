# AGENTS.md

## Cursor Cloud — Option C (cloud-only, no local PC)

Users on **Option C** do not run `install.bat` or `gem_app.py` on their computer. All GEM Logic scans run in **this Cloud VM**.

### On each Cloud Agent session (automatic layer)

The VM **update script** refreshes `.venv`, installs platform deps, and `tvdatafeed` shim.

### Run a scan for the user

```bash
cd /workspace && source .venv/bin/activate
python scripts/cloud_gem_report.py
```

Read **`reports/latest_gem_report.md`** and summarize actionable signals (EMERALD GEM, RUBY GEM, setups, entries).

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

### User-facing phrases

- "Scan my watchlist" → `cloud_gem_report.py`
- "Add TSLA" → edit `config/watchlist.json`
- They do **not** need local install steps

### GEM engine

- Code: `src/gem/` + `src/gem_platform.py`
- Defaults: RSI 14, OS 28, OB 72, 3 divergence events, 8-bar GEM window

### Data

TradingView (limited nologin) → yfinance fallback. Requires network.

### Legacy

- Old screener: `scripts/run_screener.py`
- Desktop GUI: `gem_app.py` (needs display; not used for Option C)
