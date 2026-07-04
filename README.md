# GEM Logic Platform

Desktop and CLI tools that scan **your chosen instruments** with **live market data** (TradingView / yfinance) and produce signals aligned with **GEM Logic** (RSI extremes, divergence memory, 3rd-event setups, candle confirmation, Emerald/Ruby GEM).

## Quick install

### Windows

```bat
install.bat
.venv\Scripts\activate
python gem_app.py
```

### Linux / macOS

```bash
chmod +x install.sh
./install.sh
source .venv/bin/activate
python gem_app.py
```

## Configure instruments

Edit **`config/watchlist.json`**:

```json
{
  "refresh_minutes": 5,
  "timeframe": "60",
  "bars": 120,
  "instruments": [
    {"symbol": "AAPL", "exchange": "NASDAQ", "name": "Apple"}
  ]
}
```

You can also edit the watchlist from the desktop app (**Edit watchlist…**).

## Run modes

| Mode | Command |
|------|---------|
| **Desktop (recommended)** | `python gem_app.py` |
| **CLI monitor (loop)** | `python scripts/run_gem_monitor.py` |
| **Single scan** | `python scripts/run_gem_monitor.py --once` |
| Legacy RSI screener | `python scripts/run_screener.py` |

## GEM signals (what you will see)

| Signal | Meaning |
|--------|---------|
| **EMERALD GEM** | Oversold + bullish divergence + bullish candle within confirmation window |
| **RUBY GEM** | Overbought + bearish divergence + bearish candle within window |
| **BUY/SELL SETUP (3 div)** | Third divergence event in lookback while in extreme zone |
| **LONG/SHORT ENTRY** | Breakout of setup range after setup (GEM execution model) |

Defaults match GEM Logic 1.5 Pine: RSI 14, OS 28, OB 72, lookback 84, 3 events, 8-bar GEM window.

## Data sources

1. **TradingView** via `tvdatafeed` (anonymous mode may be limited)
2. **yfinance** fallback (reliable for US equities on H1)

Internet access is required for live scans.

## Project layout

```
config/watchlist.json    # Your symbols
src/gem/                 # GEM Logic engine (Python port)
src/gem_platform.py      # Live scan orchestration
src/market_data.py       # OHLCV fetching
gem_app.py               # Desktop entry point
install.sh / install.bat # Installers
```

## Troubleshooting

- **Import `tvdatafeed` fails on Linux** — Re-run `./install.sh` (creates lowercase import shim).
- **PyQt / libEGL on Linux** — Install `libegl1` and use a desktop session, or use CLI monitor only.
- **No data for a symbol** — Check ticker and exchange; try a US symbol like `AAPL`.

## License

See repository license. Not financial advice.
