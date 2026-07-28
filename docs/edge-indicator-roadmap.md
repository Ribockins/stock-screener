# EDGE Indicator Roadmap

## Phase 0 — сейчас (GEM Logic 1.5)

- [x] RSI divergence, OB/OS 28/72
- [x] Candle confluence (Emerald / Ruby)
- [x] S/R proximity
- [x] MTF M15 / H1 / H4 / D1
- [x] GEM My List, checklist, journal

## Phase 1 — RSI + MFI (P0)

- [x] `src/edge_combos.py` — MFI, dual divergence helpers
- [ ] Подключить к скану: флаги `rsi_div`, `mfi_div`, `dual_div` в JSON отчёта
- [ ] Повысить EDGE score / strength если **dual** bear/bull
- [ ] Колонка в GEM My List: `MFI` / `Dual`

**Правило силы (черновик):**

| Условие | Бонус к narrative |
|---------|-------------------|
| RSI div only | как сейчас |
| RSI + MFI div | +1 tier или «DUAL» в Notes |
| RSI div, MFI нет | «weak money confirm» — WARNING only |

## Phase 2 — фильтры (P1)

- [ ] RSI + EMA (200/50 на H4/D1) — `against_trend` flag
- [ ] ADX + RSI — не fade если ADX > 25 и растёт
- [ ] Bollinger + RSI — `band_stretch` на H1

## Phase 3 — контекст (P2)

- [ ] VWAP + RSI на M15 (forex session)
- [ ] MACD hist + MFI
- [ ] SuperTrend + MFI (alerts)

## Phase 4 — data-heavy (P3)

- [ ] Volume Profile + RSI
- [ ] CVD + RSI
- [ ] Squeeze module

## Journal fields (после Phase 1)

Добавить в CSV: `rsi_div`, `mfi_div`, `dual_div`, `ema_filter`, `bb_stretch`.

---

Связь с книгами: dual div без исполнения = **WARNING** (Douglas); серия с dual div в журнале (Aronson).
