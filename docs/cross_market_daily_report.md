# Cross-market daily report (macro layer)

_Regenerate: `python scripts/cross_market_daily_batch.py`_

Aligned trading days (all symbols): **3021** · sample **2014–2026**

## Instruments loaded

| Symbol | From | To |
|--------|------|-----|
| **US30** | 2014-07-28 | 2026-07-24 |
| **UK100** | 2014-07-28 | 2026-07-24 |
| **FRA40** | 2014-07-28 | 2026-07-24 |
| **USOil** | 2014-07-28 | 2026-07-24 |
| **UKOil** | 2014-07-28 | 2026-07-24 |
| **XAUUSD** | 2014-07-28 | 2026-07-24 |
| **XAGUSD** | 2014-07-28 | 2026-07-24 |
| **NGAS** | 2014-07-28 | 2026-07-23 |

## Weekday bias (avg daily return %)

- **US30:** Mon +0.090% · Tue +0.017% · Wed +0.077% · Thu +0.009% · Fri +0.015%
- **UK100:** Mon +0.007% · Tue +0.045% · Wed +0.113% · Thu -0.091% · Fri +0.025%
- **FRA40:** Mon -0.034% · Tue +0.039% · Wed +0.111% · Thu -0.012% · Fri +0.036%
- **USOil:** Mon -0.091% · Tue +0.006% · Wed +0.074% · Thu +0.127% · Fri +0.088%
- **UKOil:** Mon -0.140% · Tue -0.019% · Wed +0.060% · Thu +0.135% · Fri +0.127%
- **XAUUSD:** Mon -0.001% · Tue +0.044% · Wed +0.037% · Thu +0.048% · Fri +0.080%
- **XAGUSD:** Mon +0.089% · Tue +0.009% · Wed +0.148% · Thu -0.055% · Fri +0.101%
- **NGAS:** Mon +0.233% · Tue +0.138% · Wed +0.134% · Thu -0.227% · Fri +0.039%

## Correlation (252d, daily returns)

| | US30 | UK100 | FRA40 | USOil | XAUUSD | NGAS |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| US30 | — | 0.67 | 0.70 | -0.42 | 0.32 | -0.07 |
| UK100 | 0.67 | — | 0.75 | -0.27 | 0.32 | -0.09 |
| FRA40 | 0.70 | 0.75 | — | -0.43 | 0.30 | -0.13 |
| USOil | -0.42 | -0.27 | -0.43 | — | -0.09 | 0.12 |
| XAUUSD | 0.32 | 0.32 | 0.30 | -0.09 | — | -0.01 |
| NGAS | -0.07 | -0.09 | -0.13 | 0.12 | -0.01 | — |

## Lead–lag (daily returns, full sample)

| Pair | Lag (days) | Corr | n | Read |
|------|------------|------|---|------|
| US30→UK100 | 0 | 0.76 | 3029 | same day |
| US30→FRA40 | 0 | 0.788 | 3066 | same day |
| UK100→FRA40 | 0 | 0.846 | 3023 | same day |
| US30→USOil | 5 | 0.042 | 3096 | US30 leads USOil ~5d |
| US30→XAUUSD | 0 | 0.042 | 3096 | same day |
| USOil→XAUUSD | 1 | 0.032 | 3095 | USOil leads XAUUSD ~1d |
| USOil→UKOil | 1 | 0.041 | 3096 | USOil leads UKOil ~1d |
| XAUUSD→XAGUSD | 0 | 0.775 | 3098 | same day |
| US30→NGAS | 0 | 0.063 | 3094 | same day |
| USOil→NGAS | 4 | 0.058 | 3094 | USOil leads NGAS ~4d |

## After US30 shock (next-day median return)

| Condition | Follower | n | Median | Pos% |
|-----------|----------|---|--------|------|
| US30 ≤-1% | XAUUSD | 312 | +0.128% | 56.4% |
| US30 ≤-1% | USOil | 312 | +0.062% | 51.0% |
| US30 ≤-1% | UK100 | 312 | +0.106% | 52.9% |
| US30 ≤-1% | NGAS | 312 | -0.456% | 44.9% |
| US30 ≤-1% | FRA40 | 312 | +0.207% | 56.4% |
| US30 ≥1% | XAUUSD | 354 | +0.068% | 52.3% |
| US30 ≥1% | USOil | 354 | -0.122% | 48.6% |

**Brent–WTI:** daily return corr **-0.17** (252d: **0.943**).

## How this feeds GEM + VECTOR

1. **Macro filter:** on US30 down days, gold/oil next-day stats above → bias for mean-reversion or continuation per pair.
2. **EU vs US:** UK100/FRA40 lead-lag vs US30 → which index to watch first in London vs NY handoff.
3. **Intraday execution** still from `cross_market_profile_batch.py` (1m/5m); daily layer sets **directional prior** only.

JSON: `reports/cross_market_daily.json`