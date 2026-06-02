# AGENTS.md

## Cursor Cloud specific instructions

### What this repo is

Python **RSI & divergence stock screener** (H1 timeframe). Main entry points:

| Surface | Command |
|---------|---------|
| CLI one-shot scan | `python scripts/run_screener.py` |
| CLI scheduler | `python scripts/schedule_screener.py` |
| Desktop UI (PyQt6) | `python desktop_app.py` |

Config: `rsiconfig.py` and optional `.env` (copy from `.env.example`). Default DB is **SQLite** (`screener.db`).

### Environment bootstrap (first time)

1. **Virtualenv** — `python3-venv` may be missing; use `virtualenv` from `~/.local/bin` (install with `pip install --user virtualenv` if needed).
2. **Activate** — `source .venv/bin/activate` from repo root (`/workspace`).
3. **`tvdatafeed`** — Not on PyPI at the pinned version. Install from GitHub:
   `pip install --no-cache-dir git+https://github.com/rongardF/tvdatafeed.git`
4. **Linux import shim** — The repo imports `tvdatafeed` (lowercase) but the package exposes `tvDatafeed`. After installing, add a venv-only shim (do not commit):
   ```bash
   SHIM="$(python -c 'import site; print(site.getsitepackages()[0])')/tvdatafeed"
   mkdir -p "$SHIM"
   echo 'from tvDatafeed import *' > "$SHIM/__init__.py"
   ```
5. **Other Python deps** — `pip install -r requirements.txt` fails on Python 3.12 (pinned `pandas`/`numpy`/`tvdatafeed`/`ta-lib`). Install unpinned runtime deps instead (see update script). **`ta-lib` is listed but unused** (RSI is pure pandas); skip unless you add TA-Lib system libs.
6. **Desktop** — `pip install -r requirements_desktop.txt` (same caveats). Requires **GUI display** (`DISPLAY` set) and system GL libs (e.g. `libegl1`); without them PyQt6 exits with `libEGL.so.1` errors.
7. **Stock lists** — `rsiconfig.STOCK_LISTS` expects `data/stocks/*.txt` (one symbol per line). The repo ships only `.gitkeep`; create local lists before scanning.

### Running services

No Docker or separate servers. A single Python process plus **outbound network** (TradingView via `tvdatafeed`, **yfinance** fallback).

- **CLI scan**: `source .venv/bin/activate && python scripts/run_screener.py`
- **Desktop**: `source .venv/bin/activate && python desktop_app.py` (needs display + EGL)

### Lint / tests

There is **no** configured linter, pre-commit, or automated test suite. Use `python -m compileall -q src scripts desktop_app.py rsiconfig.py` as a quick syntax check.

### Gotchas discovered on Cloud VMs

- SQLite schema in `database.py` must use separate `CREATE INDEX` statements (inline `INDEX` in `CREATE TABLE` is invalid in SQLite).
- Newer **yfinance** returns MultiIndex/extra columns; `data_fetcher._fetch_from_yfinance` must flatten columns before renaming.
- TradingView nologin mode often fails; **yfinance fallback** is what makes scans succeed in practice.
