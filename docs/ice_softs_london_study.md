# ICE softs London open — study notes (Coffee KCU26 / Cocoa CCU26)

Persistent summary of backtests on user-supplied **1-minute ICE** exports (Jan–Jul 2026).  
Re-run: `python scripts/ice_softs_analyze.py --coffee PATH --cocoa PATH`

## Data files (user uploads)

| Instrument | Contract | Typical first bar (winter / summer in file) |
|------------|----------|---------------------------------------------|
| Coffee Arabica | KCU26 | **09:15** (GMT) / **08:15** (after UK BST → file often **UTC**) |
| NY Cocoa | CCU26 | **09:45** / **08:45** |

**Timezone:** From **~30 Mar 2026**, first daily bar shifts **−1 hour** in the file (08:15 / 08:45) while winter shows 09:15 / 09:45. Treat as **same London wall-clock open** if export is UTC.

Verified duplicate uploads (identical bytes): `NY_Cocoa_CCU26-ICEUS_6e63`, `cocoa_CCU26-ICEUS_dbc5`, `cocoa_CCU26-ICEUS_2c13`; coffee `Coffee_Arabica_KCU26-a4e6`, `coffe_KCU26-ICEUS_7548`.

## Core hypotheses tested

### 1) Cocoa-only fade after open (main hope)

- **Rule:** |impulse 0–10m after open| ≥ 0.10%; **fade** from minute 10; exit **+45m** from open.
- **~110** Mon–Fri sessions with impulse.
- **Win fade ≈ 51%** (not ~70%).
- **Retrace ≥50% of impulse by +45m ≈ 21%**; **≥80% ≈ 18%**.
- **Monday** best fade win (~59%); **Thursday** weakest (~38%).

### 2) Coffee 0–5m vs cocoa 0–5m (same direction)

File times **08:15→08:20** (KC) vs **08:45→08:50** (CC), **74** days:

- **Same first impulse direction: 26/74 = 35%** (often **opposite**, not copy).
- Monday **50%**, Tuesday **~24%**.

### 3) Coffee lead 30m before cocoa → cocoa repeats

- Coffee **09:15→09:45** (or 08:15→08:45) vs cocoa **+30m** after cocoa open: **~47–53%** same direction — **not** a signal.
- **“Coffee reversed → only trade cocoa fade”** on Yahoo/ICE: **no improvement** vs fading cocoa every day.

### 4) London anchors (fade 10m impulse)

| Anchor (file winter) | Cocoa fade win (ICE) | Notes |
|----------------------|----------------------|--------|
| 09:45 | ~50% | Primary cocoa open |
| 11:00 | ~53% win, weak avg PnL | |
| 13:30 / 14:30 | ~44–47% | US macro / cash open overlap |

### 5) Raw **08:45** cocoa (summer labels)

- Fade 08:45→08:50 move, exit +45m: **~54%** win (74 days).
- Coffee 08:15→08:20 fade: **~51%**, ~0 pts.

## Practical rules (research / paper only)

1. **Do not** copy coffee direction into cocoa at open (35% same 5m on 08:xx set).
2. **Cocoa-only:** wait **10m**, fade impulse, target **+30–45m**; expect **~50%** wins — use **stops** and **day filter** (Mon better, Thu cautious).
3. **Deep mean reversion (80%)** is **rare (~18%)** — do not size for 70% full retrace.
4. Normalize **UTC vs London** when mixing winter/summer rows.

## Reports generated in VM

- `reports/ice_softs_london_anchors.csv`
- `reports/coffee_cocoa_same_impulse_5m_0815_0845.csv`
- `reports/coffee_cocoa_repeat_reversal.csv`
- `reports/ice_0815_0845_three_tests.csv`
- `reports/cocoa_0945_open_by_weekday.csv`
