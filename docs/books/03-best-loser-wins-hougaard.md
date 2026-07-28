# Best Loser Wins — Tom Hougaard

| Поле | Данные |
|------|--------|
| **Название** | Best Loser Wins: Why Normal Thinking Never Wins the Trading Game |
| **Автор** | Tom Hougaard |
| **Год** | 2022 |
| **Тема** | Убытки, mental toughness, anti «normal thinking» |
| **Полезность для EDGE** | Очень высокая — **как проигрывать** по системе |

---

## Главная идея

Успех зависит не от того, **как вы выигрываете**, а от того, **как вы проигрываете**.

**Best loser wins** = быстро признать ошибку, не раздувать loss, не мстить рынку, дать прибыли место, не ломать систему после серии лоссов.

---

## Нормальное мышление vs рынок

| Обычное | Нужно в трейдинге |
|---------|-------------------|
| Быть правым | Вероятность |
| Убрать боль | Принять дискомфорт |
| Быстро забрать профит | Дать победителю место |
| Не признавать ошибку | Быстрый stop |

---

## Для EDGE

1. **Score / PREMIUM не отменяет stop** — один loss в серии нормален.
2. **Журнал: Loss Quality** — отделить плохую систему от плохого исполнения.
3. **Не менять код после 1–3 лоссов** — минимум 30–50 сигналов (см. `discipline.json`).
4. **Confirmed vs live** — наблюдение на формирующейся свече, действие после закрытия.

### Good loss vs Bad loss

| Тип | Пример |
|-----|--------|
| **Good loss** | Вход по правилу, SL сработал, risk принят |
| **Bad loss** | Раньше trigger, перенос SL, revenge size, без stop |

Правило библиотеки:

> **Good loss is part of the system.**  
> **Bad loss is violation of the system.**

---

## Внедрено в проект

- Колонки журнала: `entry_trigger`, `loss_quality`, `mistake`
- `config/discipline.json`: `no_martingale`, `no_widen_stop`, `min_signals_before_code_change`
- Будущий dashboard: win rate и avg R по strength + доля good losses

---

## Оценка

| Критерий | Оценка |
|----------|--------|
| Принятие убытков | 10/10 |
| EDGE execution | 10/10 |
| MT4 risk | 9/10 |
| Pine / формула | 4/10 |
| Journal | 9/10 |

**Вывод:** книга №3 — слой **качества проигрыша** поверх Douglas №1–2.
