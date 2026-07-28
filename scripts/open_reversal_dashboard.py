#!/usr/bin/env python3
"""Build Open Reversal presentation dashboard (Coffee KCU26 / Cocoa CCU26 ICE 1m studies)."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
REPORTS = REPO / "reports"

WD_RU = {
    "Monday": "Понедельник",
    "Tuesday": "Вторник",
    "Wednesday": "Среда",
    "Thursday": "Четверг",
    "Friday": "Пятница",
}


@dataclass
class Rating:
    dots: str
    label: str
    css: str  # row-accent-green | row-accent-blue | row-accent-yellow | row-accent-red | row-neutral


def rate_pct(pct: float, *, strong: float = 75, good: float = 55, mid: float = 40) -> Rating:
  if pct >= strong:
    return Rating("🟢🟢🟢🟢🟢", "ОЧЕНЬ СИЛЬНО", "row-accent-green")
  if pct >= good:
    return Rating("🟢🟢🟢🟢", "Отлично", "row-accent-green")
  if pct >= mid:
    return Rating("🟢🟢🟢", "Хорошо", "row-accent-green")
  if pct >= 30:
    return Rating("🔵🔵🔵", "Средне / контекст", "row-accent-blue")
  if pct >= 20:
    return Rating("🟡🟡", "Слабо", "row-accent-yellow")
  return Rating("🔴", "Осторожно", "row-accent-red")


def rate_time_zone(strength: int) -> Rating:
  """strength 1–5 for reversal timing windows."""
  maps = {
    1: Rating("🟡", "Низкая", "row-accent-yellow"),
    2: Rating("🟢", "Растёт", "row-accent-green"),
    3: Rating("🟢🟢🟢", "Высокая", "row-accent-green"),
    4: Rating("🟢🟢🟢🟢", "Очень высокая", "row-accent-green"),
    5: Rating("🟢🟢🟢🟢🟢", "Главная зона", "row-accent-green"),
  }
  return maps.get(strength, Rating("⚪", "—", "row-neutral"))


def cell_heat(pct: float, *, invert: bool = False) -> str:
  v = 100 - pct if invert else pct
  if v >= 60:
    return "heat-5"
  if v >= 50:
    return "heat-4"
  if v >= 42:
    return "heat-3"
  if v >= 35:
    return "heat-2"
  return "heat-1"


def load_metrics(reports: Path) -> dict:
  cocoa_open = pd.read_csv(reports / "cocoa_0945_open_by_weekday.csv", parse_dates=["day"])
  noon = pd.read_csv(reports / "cocoa_open_to_noon_retrace.csv", parse_dates=["day"])
  repeat = pd.read_csv(reports / "coffee_cocoa_repeat_reversal.csv", parse_dates=["day"])
  same5 = pd.read_csv(reports / "coffee_cocoa_same_impulse_5m_0815_0845.csv")
  wd_noon = pd.read_csv(reports / "cocoa_noon_retrace_by_weekday.csv")
  anchors = pd.read_csv(reports / "ice_softs_london_anchors.csv", parse_dates=["day"])

  cocoa_open["ge50_45"] = cocoa_open["retrace_pct_45"] >= 50
  merged = repeat.merge(noon[["day", "ge50_best", "ge50_noon"]], on="day", how="inner")

  n_days = len(noon)
  cocoa_ge50_best = float(noon["ge50_best"].mean() * 100)
  cocoa_ge50_noon = float(noon["ge50_noon"].mean() * 100)
  coffee_rev30 = float(merged["k_reversal_30"].mean() * 100) if len(merged) else 0.0
  either_ge50 = float((merged["ge50_best"] | merged["k_reversal_30"]).mean() * 100) if len(merged) else 0.0
  both_ge50 = float((merged["ge50_best"] & merged["k_reversal_30"]).mean() * 100) if len(merged) else 0.0
  same_impulse = float(same5["same_impulse"].mean() * 100) if len(same5) else 0.0

  c_fade = anchors[(anchors["instrument"] == "cocoa") & (anchors["anchor"] == "09:45")]
  k_fade = anchors[(anchors["instrument"] == "coffee") & (anchors["anchor"] == "09:45")]
  cocoa_fade_win = float(c_fade["win"].mean() * 100) if len(c_fade) else 0.0
  coffee_fade_win = float(k_fade["win"].mean() * 100) if len(k_fade) else 0.0

  med_rev_start = float(cocoa_open["rev_start_m"].median())

  time_rows = []
  for lo, hi, label, strength in [
    (0, 5, "0–5 мин", 1),
    (5, 10, "5–10 мин", 2),
    (10, 15, "10–15 мин", 5),
    (15, 20, "15–20 мин", 4),
    (20, 30, "20–30 мин", 3),
    (30, 60, "30–60 мин", 1),
  ]:
    mask = (cocoa_open["rev_start_m"] >= lo) & (cocoa_open["rev_start_m"] < hi)
    share = float(mask.mean() * 100)
    ge50_in = float((mask & cocoa_open["ge50_45"]).sum() / max(mask.sum(), 1) * 100)
    time_rows.append(
      {
        "window": label,
        "share_start_pct": round(share, 1),
        "ge50_in_window_pct": round(ge50_in, 1),
        "strength": strength,
      }
    )

  weekday_rows = []
  order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
  for day in order:
    row = wd_noon[wd_noon["day"] == day]
    if row.empty:
      continue
    r = row.iloc[0]
    weekday_rows.append(
      {
        "day_en": day,
        "day_ru": WD_RU.get(day, day),
        "n": int(r["n"]),
        "ge50_noon_pct": round(float(r["ge50_noon_pct"]), 1),
        "ge50_best_pct": round(float(r["ge50_best_pct"]), 1),
        "slowing_pct": round(float(r["slowing_pct"]), 1),
      }
    )

  return {
    "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    "n_sessions": n_days,
    "n_cocoa_open": len(cocoa_open),
    "n_merged": len(merged),
    "either_ge50_pct": round(either_ge50, 1),
    "cocoa_ge50_best_pct": round(cocoa_ge50_best, 1),
    "cocoa_ge50_noon_pct": round(cocoa_ge50_noon, 1),
    "coffee_rev30_pct": round(coffee_rev30, 1),
    "both_ge50_pct": round(both_ge50, 1),
    "same_5m_impulse_pct": round(same_impulse, 1),
    "cocoa_fade_win_pct": round(cocoa_fade_win, 1),
    "coffee_fade_win_pct": round(coffee_fade_win, 1),
    "median_rev_start_min": round(med_rev_start, 0),
    "time_windows": time_rows,
    "weekdays": weekday_rows,
  }


def render_html(m: dict) -> str:
  def row_metric(metric: str, value: str, rating: Rating, note: str = "") -> str:
    note_cell = f'<span class="note">{note}</span>' if note else ""
    return f"""<tr class="{rating.css}">
      <td class="metric">{metric}</td>
      <td class="value">{value}</td>
      <td class="dots">{rating.dots}</td>
      <td class="label">{rating.label}{note_cell}</td>
    </tr>"""

  summary_rows = [
    row_metric("Дней в анализе (открытие → полдень)", str(m["n_sessions"]), Rating("⚪", "Справка", "row-neutral")),
    row_metric(
      "Разворот ≥50% хотя бы на одном рынке",
      f"{m['either_ge50_pct']}%",
      rate_pct(m["either_ge50_pct"], strong=80, good=65),
      "cocoa max до 12:00 ∨ coffee 30m",
    ),
    row_metric(
      "Cocoa — откат ≥50% (лучший до 12:00)",
      f"{m['cocoa_ge50_best_pct']}%",
      rate_pct(m["cocoa_ge50_best_pct"]),
    ),
    row_metric(
      "Cocoa — откат ≥50% именно к 12:00",
      f"{m['cocoa_ge50_noon_pct']}%",
      rate_pct(m["cocoa_ge50_noon_pct"], strong=55, good=45, mid=35),
    ),
    row_metric(
      "Coffee — разворот 30m после открытия",
      f"{m['coffee_rev30_pct']}%",
      rate_pct(m["coffee_rev30_pct"], strong=55, good=45, mid=35),
    ),
    row_metric(
      "Одновременно cocoa ≥50% и coffee разворот",
      f"{m['both_ge50_pct']}%",
      rate_pct(m["both_ge50_pct"], strong=50, good=35, mid=25),
      "синхронность",
    ),
    row_metric(
      "Одинаковый импульс 5m (08:15 / 08:45)",
      f"{m['same_5m_impulse_pct']}%",
      rate_pct(m["same_5m_impulse_pct"], strong=55, good=45, mid=35),
      "часто противоположно",
    ),
  ]

  time_rows_html = []
  for tw in m["time_windows"]:
    r = rate_time_zone(tw["strength"])
    time_rows_html.append(
      f"""<tr class="{r.css}">
        <td>{tw['window']}</td>
        <td>{tw['share_start_pct']}% дней</td>
        <td class="dots">{r.dots}</td>
        <td>{r.label}</td>
      </tr>"""
    )

  wd_html = []
  for w in m["weekdays"]:
    wd_html.append(
      f"""<tr>
        <td class="wday">{w['day_ru']}</td>
        <td class="n">{w['n']}</td>
        <td class="{cell_heat(w['ge50_noon_pct'])}">{w['ge50_noon_pct']}%</td>
        <td class="{cell_heat(w['ge50_best_pct'])}">{w['ge50_best_pct']}%</td>
        <td class="{cell_heat(w['slowing_pct'])}">{w['slowing_pct']}%</td>
      </tr>"""
    )

  status_rows = [
    ("🚀 Сильный импульс после открытия", "🔴", "Ждём", "row-accent-red"),
    ("Импульс начинает слабеть (15–45m)", "🟡", "Внимание", "row-accent-yellow"),
    ("Цена не обновляет экстремум", "🔵", "Готовимся", "row-accent-blue"),
    ("Первая уверенная свеча обратно (~10m+)", "🟢", "Возможный вход", "row-accent-green"),
    ("Откат ≥50% от импульса", "🟢🟢🟢", "Цель / фиксация", "row-accent-green"),
  ]
  status_html = "\n".join(
    f'<tr class="{css}"><td>{t}</td><td class="dots">{d}</td><td>{a}</td></tr>' for t, d, a, css in status_rows
  )

  return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>OPEN REVERSAL ENGINE — Coffee &amp; Cocoa</title>
  <style>
    :root {{
      --bg: #0b0f14;
      --panel: #121a24;
      --border: #243044;
      --text: #e8eef7;
      --muted: #8fa3bf;
      --green: #1f8f5f;
      --green-bg: rgba(31, 143, 95, 0.18);
      --blue: #2d7dd2;
      --blue-bg: rgba(45, 125, 210, 0.16);
      --yellow: #c9a227;
      --yellow-bg: rgba(201, 162, 39, 0.15);
      --red: #d64550;
      --red-bg: rgba(214, 69, 80, 0.16);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0; padding: 24px;
      font-family: "Segoe UI", system-ui, sans-serif;
      background: radial-gradient(1200px 600px at 10% -10%, #1a2740 0%, var(--bg) 55%);
      color: var(--text);
      line-height: 1.45;
    }}
    h1 {{ font-size: 1.55rem; margin: 0 0 4px; letter-spacing: 0.02em; }}
    .sub {{ color: var(--muted); margin-bottom: 20px; font-size: 0.92rem; }}
    .grid {{ display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); }}
    section {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 14px 16px 10px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.25);
    }}
    section h2 {{
      margin: 0 0 10px;
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: var(--muted);
    }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; }}
    th, td {{ padding: 8px 10px; border-bottom: 1px solid var(--border); text-align: left; }}
    th {{ color: var(--muted); font-weight: 600; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.06em; }}
    tr:last-child td {{ border-bottom: none; }}
    .metric {{ font-weight: 500; }}
    .value {{ font-variant-numeric: tabular-nums; font-weight: 700; }}
    .dots {{ white-space: nowrap; }}
    .label {{ color: var(--muted); font-size: 0.85rem; }}
    .note {{ display: block; font-size: 0.75rem; opacity: 0.85; }}
    .row-accent-green td {{ background: var(--green-bg); }}
    .row-accent-blue td {{ background: var(--blue-bg); }}
    .row-accent-yellow td {{ background: var(--yellow-bg); }}
    .row-accent-red td {{ background: var(--red-bg); }}
    .row-neutral td {{ background: rgba(255,255,255,0.03); }}
    .engine {{
      display: flex; flex-wrap: wrap; gap: 20px; align-items: center;
      padding: 16px 18px; margin-bottom: 16px;
      background: linear-gradient(90deg, #101820, #152433);
      border: 1px solid var(--border); border-radius: 12px;
    }}
    .engine .pill {{
      padding: 10px 14px; border-radius: 8px; border: 1px solid var(--border);
      min-width: 140px;
    }}
    .engine .pill strong {{ display: block; font-size: 1.35rem; }}
    .engine .pill span {{ color: var(--muted); font-size: 0.8rem; }}
    .timeline {{
      font-family: ui-monospace, monospace; font-size: 0.72rem;
      background: #0a1018; border-radius: 8px; padding: 12px; border: 1px solid var(--border);
      white-space: pre; overflow-x: auto; color: #b8c9e0;
    }}
    .heat-5 {{ background: rgba(31, 143, 95, 0.45); font-weight: 700; }}
    .heat-4 {{ background: rgba(31, 143, 95, 0.28); }}
    .heat-3 {{ background: rgba(45, 125, 210, 0.22); }}
    .heat-2 {{ background: rgba(201, 162, 39, 0.18); }}
    .heat-1 {{ background: rgba(214, 69, 80, 0.2); }}
    .wday {{ font-weight: 600; }}
    .n {{ color: var(--muted); }}
    footer {{ margin-top: 18px; color: var(--muted); font-size: 0.75rem; }}
  </style>
</head>
<body>
  <h1>☕ COFFEE &amp; 🍫 COCOA — OPEN REVERSAL DASHBOARD</h1>
  <p class="sub">ICE 1m · KCU26 / CCU26 · London open · сгенерировано {m['generated_utc']}</p>

  <div class="engine">
    <div class="pill"><span>Coffee fade @09:45</span><strong>🟢 {m['coffee_fade_win_pct']}%</strong></div>
    <div class="pill"><span>Cocoa fade @09:45</span><strong>🟢 {m['cocoa_fade_win_pct']}%</strong></div>
    <div class="pill"><span>Combined ≥50%</span><strong>🟢🟢 {m['either_ge50_pct']}%</strong></div>
    <div class="pill"><span>Медиана старта разворота</span><strong>🔵 ~{int(m['median_rev_start_min'])} мин</strong></div>
  </div>

  <div class="grid">
    <section class="full" style="grid-column: 1 / -1;">
      <h2>📊 Сводка — 5 секунд</h2>
      <table>
        <thead><tr><th>Метрика</th><th>Результат</th><th>Индикатор</th><th>Оценка</th></tr></thead>
        <tbody>
          {''.join(summary_rows)}
        </tbody>
      </table>
    </section>

    <section>
      <h2>⏰ Время разворота (cocoa)</h2>
      <table>
        <thead><tr><th>После открытия</th><th>Доля стартов</th><th></th><th>Зона</th></tr></thead>
        <tbody>{''.join(time_rows_html)}</tbody>
      </table>
    </section>

    <section>
      <h2>🎯 Рабочее окно</h2>
      <div class="timeline">Открытие
│  Первое движение ██████
├────► 5 мин   🟡 импульс
├────► 10 мин  🟢🟢🟢🟢🟢  ГЛАВНАЯ ЗОНА (10–20 мин)
├────► 20 мин  🟢🟢🟢🟢
├────► 30 мин  🟢🟢🟢
└────► 60 мин  🟡 поздно</div>
      <p class="sub" style="margin:10px 0 0">Окно входа: <strong>5–30 мин</strong> после открытия cocoa; лучшее ядро <strong>10–20 мин</strong>.</p>
    </section>

    <section>
      <h2>📅 Откат к 12:00 по дням недели</h2>
      <table>
        <thead>
          <tr><th>День</th><th>N</th><th>≥50% к 12:00</th><th>≥50% max до 12</th><th>Замедление</th></tr>
        </thead>
        <tbody>{''.join(wd_html)}</tbody>
      </table>
      <p class="sub" style="margin-top:8px">Лучше: <strong>Пн</strong> · Слабее к полудню: <strong>Пт, Вт</strong></p>
    </section>

    <section>
      <h2>🚦 Готовность к входу</h2>
      <table>
        <thead><tr><th>Сигнал</th><th></th><th>Действие</th></tr></thead>
        <tbody>{status_html}</tbody>
      </table>
    </section>

    <section>
      <h2>⭐ Итог</h2>
      <table>
        <tbody>
          <tr class="row-accent-green"><td>Импульс после открытия почти всегда есть</td><td class="dots">🟢</td></tr>
          <tr class="row-accent-green"><td>Часто следует замедление (15–45m)</td><td class="dots">🟢</td></tr>
          <tr class="row-accent-green"><td>Откат ≥50% до полудня (cocoa max) — очень часто</td><td class="dots">🟢🟢🟢🟢</td></tr>
          <tr class="row-accent-blue"><td>Не копировать coffee → cocoa в первые 5m ({m['same_5m_impulse_pct']}% same)</td><td class="dots">🔵</td></tr>
          <tr class="row-accent-yellow"><td>После 30m вероятность «раннего» сетапа падает</td><td class="dots">🟡</td></tr>
        </tbody>
      </table>
    </section>
  </div>

  <footer>
    Источник: reports/*.csv · Пересборка: <code>python scripts/open_reversal_dashboard.py</code>
    · Исследование, не торговый совет.
  </footer>
</body>
</html>"""


def main() -> int:
  parser = argparse.ArgumentParser(description="Generate Open Reversal HTML dashboard")
  parser.add_argument("--reports", type=Path, default=REPORTS)
  parser.add_argument("-o", "--output", type=Path, default=REPORTS / "open_reversal_dashboard.html")
  parser.add_argument("--json", type=Path, default=None, help="Optional metrics JSON dump")
  args = parser.parse_args()

  metrics = load_metrics(args.reports)
  html = render_html(metrics)
  args.output.parent.mkdir(parents=True, exist_ok=True)
  args.output.write_text(html, encoding="utf-8")
  print(f"Wrote {args.output}")

  if args.json:
    payload = {k: v for k, v in metrics.items()}
    args.json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {args.json}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
