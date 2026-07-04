"""Build balanced synthetic pair indices (A10 / B12) from a stock pool."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent
UNIVERSE_PATH = ROOT / "config" / "pair_universe_140.json"
INDEX_TARGET = 10_000.0
MIN_PER_INDEX = 10
MAX_PER_INDEX = 15
# Compact channel pair: fewer names, wider oscillating spread
CHANNEL_MIN_PER_INDEX = 5
CHANNEL_MAX_PER_INDEX = 7
MIN_CHANNEL_CORR = 0.80
MIN_CHANNEL_R2 = 0.82


@dataclass
class StockMeta:
    symbol: str
    name: str
    sector: str
    region: str
    price: float
    market_cap: float
    volume: float
    weight: float = 0.0


@dataclass
class SyntheticIndex:
    code: str
    name: str
    members: List[StockMeta] = field(default_factory=list)

    @property
    def n(self) -> int:
        return len(self.members)

    def totals(self) -> Dict[str, float]:
        return {
            "price_sum": sum(s.price for s in self.members),
            "market_cap": sum(s.market_cap for s in self.members),
            "volume": sum(s.volume for s in self.members),
        }

    def sector_weights(self) -> Dict[str, float]:
        cap = sum(s.market_cap for s in self.members) or 1.0
        out: Dict[str, float] = {}
        for s in self.members:
            out[s.sector] = out.get(s.sector, 0.0) + s.market_cap / cap
        return out


@dataclass
class PairBuildResult:
    index_a: SyntheticIndex
    index_b: SyntheticIndex
    pool_size: int
    valid_pool: int
    balance: Dict[str, Dict[str, float]]


def load_universe(path: Path = UNIVERSE_PATH) -> List[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for item in data.get("ftse_100", []):
        rows.append({**item, "region": "UK"})
    for item in data.get("cac_40", []):
        rows.append({**item, "region": "FR"})
    return rows


def fetch_stock_meta(row: dict) -> Optional[StockMeta]:
    sym = row["symbol"]
    try:
        t = yf.Ticker(sym)
        info = t.info or {}
        hist = t.history(period="5d")
        if hist.empty:
            return None
        price = float(hist["Close"].iloc[-1])
        cap = float(info.get("marketCap") or info.get("enterpriseValue") or 0)
        vol = float(info.get("averageVolume") or info.get("volume") or 0)
        if hist["Volume"].notna().any():
            vol = max(vol, float(hist["Volume"].mean()))
        if cap <= 0 or price <= 0:
            return None
        sector = row.get("sector") or info.get("sector") or "Unknown"
        return StockMeta(
            symbol=sym,
            name=row.get("name", sym),
            sector=sector,
            region=row.get("region", ""),
            price=price,
            market_cap=cap,
            volume=vol,
        )
    except Exception:
        return None


def fetch_pool_metadata(rows: List[dict], max_stocks: Optional[int] = None) -> List[StockMeta]:
    pool: List[StockMeta] = []
    for row in rows:
        m = fetch_stock_meta(row)
        if m:
            pool.append(m)
        if max_stocks and len(pool) >= max_stocks:
            break
    total_cap = sum(s.market_cap for s in pool) or 1.0
    for s in pool:
        s.weight = s.market_cap / total_cap
    return pool


def _sector_groups(pool: List[StockMeta]) -> Dict[str, List[StockMeta]]:
    g: Dict[str, List[StockMeta]] = {}
    for s in pool:
        g.setdefault(s.sector, []).append(s)
    for sec in g:
        g[sec].sort(key=lambda x: -x.market_cap)
    return g


def _imbalance(a: List[StockMeta], b: List[StockMeta], *, channel: bool = False) -> float:
    min_n = CHANNEL_MIN_PER_INDEX if channel else MIN_PER_INDEX
    max_n = CHANNEL_MAX_PER_INDEX if channel else MAX_PER_INDEX
    target_n = (min_n + max_n) / 2
    ta = sum(s.market_cap for s in a)
    tb = sum(s.market_cap for s in b)
    pa = sum(s.price for s in a)
    pb = sum(s.price for s in b)
    va = sum(s.volume for s in a)
    vb = sum(s.volume for s in b)
    # sector weight L2 distance
    wa = {}
    ca = ta or 1
    for s in a:
        wa[s.sector] = wa.get(s.sector, 0) + s.market_cap / ca
    wb = {}
    cb = tb or 1
    for s in b:
        wb[s.sector] = wb.get(s.sector, 0) + s.market_cap / cb
    sectors = set(wa) | set(wb)
    sec_pen = sum((wa.get(s, 0) - wb.get(s, 0)) ** 2 for s in sectors)
    cap_r = (ta - tb) / max(ta, tb, 1)
    price_r = (pa - pb) / max(pa, pb, 1)
    vol_r = (va - vb) / max(va, vb, 1)
    size_pen = 0.0
    if not (min_n <= len(a) <= max_n):
        size_pen += abs(len(a) - target_n) * 5
    if not (min_n <= len(b) <= max_n):
        size_pen += abs(len(b) - target_n) * 5
    return abs(cap_r) * 3 + abs(price_r) * 2 + abs(vol_r) + sec_pen * 4 + size_pen


def build_balanced_pair(pool: List[StockMeta], seed: int = 42) -> Tuple[List[StockMeta], List[StockMeta]]:
    """Greedy sector-alternate split + local swap search."""
    random.seed(seed)
    np.random.seed(seed)
    groups = _sector_groups(pool)
    a: List[StockMeta] = []
    b: List[StockMeta] = []
    for _sec, stocks in sorted(groups.items()):
        for i, s in enumerate(stocks):
            (a if i % 2 == 0 else b).append(s)

    # Trim to max size — drop smallest cap from larger side
    for side in (a, b):
        side.sort(key=lambda x: -x.market_cap)
    while len(a) > MAX_PER_INDEX:
        a.pop()
    while len(b) > MAX_PER_INDEX:
        b.pop()

    # Pad to min size from unused pool
    used = {s.symbol for s in a + b}
    unused = [s for s in pool if s.symbol not in used]
    unused.sort(key=lambda x: -x.market_cap)

    def pad(side: List[StockMeta], other: List[StockMeta]):
        while len(side) < MIN_PER_INDEX and unused:
            best_i = 0
            best_score = float("inf")
            for i, cand in enumerate(unused[:30]):
                trial = side + [cand]
                sc = _imbalance(trial, other)
                if sc < best_score:
                    best_score, best_i = sc, i
            side.append(unused.pop(best_i))

    pad(a, b)
    pad(b, a)

    # Local swap optimization
    best_score = _imbalance(a, b)
    for _ in range(400):
        if not a or not b:
            break
        ia, ib = random.randrange(len(a)), random.randrange(len(b))
        if a[ia].sector != b[ib].sector:
            continue
        a[ia], b[ib] = b[ib], a[ia]
        sc = _imbalance(a, b)
        if sc < best_score:
            best_score = sc
        else:
            a[ia], b[ib] = b[ib], a[ia]

    return a, b


def build_pair_indices(
    pool: List[StockMeta],
    code_a: str = "A10",
    code_b: str = "B12",
) -> PairBuildResult:
    a_list, b_list = build_balanced_pair(pool)
    idx_a = SyntheticIndex(code=code_a, name=f"Synthetic {code_a}", members=a_list)
    idx_b = SyntheticIndex(code=code_b, name=f"Synthetic {code_b}", members=b_list)
    ta, tb = idx_a.totals(), idx_b.totals()
    balance = {
        "A10": {**ta, "n": idx_a.n, "sectors": idx_a.sector_weights()},
        "B12": {**tb, "n": idx_b.n, "sectors": idx_b.sector_weights()},
        "ratios": {
            "cap_a_over_b": round(ta["market_cap"] / max(tb["market_cap"], 1), 4),
            "price_a_over_b": round(ta["price_sum"] / max(tb["price_sum"], 1), 4),
            "volume_a_over_b": round(ta["volume"] / max(tb["volume"], 1), 4),
        },
    }
    return PairBuildResult(
        index_a=idx_a,
        index_b=idx_b,
        pool_size=len(pool) + (140 - len(pool)),  # approximate
        valid_pool=len(pool),
        balance=balance,
    )


def cap_weighted_series(
    members: List[StockMeta],
    prices: pd.DataFrame,
    base_level: float = INDEX_TARGET,
) -> pd.Series:
    """Cap-weighted synthetic index level aligned to *base_level* at first bar."""
    caps = np.array([m.market_cap for m in members])
    w = caps / caps.sum()
    syms = [m.symbol for m in members]
    sub = prices[syms].dropna(how="any")
    if sub.empty:
        return pd.Series(dtype=float)
    rets = sub.pct_change().fillna(0.0)
    port_ret = (rets * w).sum(axis=1)
    level = (1 + port_ret).cumprod() * base_level
    level.iloc[0] = base_level
    return level


def fetch_history(symbols: List[str], months: int = 2, interval: str = "1h") -> pd.DataFrame:
    from datetime import datetime, timedelta, timezone

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=months * 31)
    frames = []
    for sym in symbols:
        df = yf.download(
            sym,
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            interval=interval,
            progress=False,
            auto_adjust=True,
            threads=False,
        )
        if df is None or df.empty:
            continue
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        s = df["Close"].rename(sym)
        frames.append(s)
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, axis=1).sort_index()
    return out.ffill().dropna(how="any")


def _align_levels(level_a: pd.Series, level_b: pd.Series) -> Tuple[pd.Series, pd.Series]:
    df = pd.concat([level_a.rename("a"), level_b.rename("b")], axis=1).dropna()
    if df.empty:
        return level_a.iloc[:0], level_b.iloc[:0]
    return df["a"], df["b"]


def channel_metrics(level_a: pd.Series, level_b: pd.Series) -> Dict:
    """Score how straight/wide the spread channel is (for pair trading)."""
    level_a, level_b = _align_levels(level_a, level_b)
    if len(level_a) < 30:
        return {"channel_score": 0.0}
    spread = level_a - level_b
    spread_range = float(spread.max() - spread.min())
    spread_std = float(spread.std()) or 1.0
    x = np.arange(len(spread), dtype=float)
    slope = float(np.polyfit(x, spread.values, 1)[0])
    total_drift = abs(slope * len(spread))
    drift_ratio = total_drift / max(spread_range, 1.0)
    ret_a, ret_b = level_a.pct_change(), level_b.pct_change()
    corr = float(ret_a.corr(ret_b)) if not ret_a.isna().all() else 0.0
    line_r2 = float(np.corrcoef(level_a.values, level_b.values)[0, 1] ** 2)
    roll = min(48, max(12, len(spread) // 8))
    z = (spread - spread.rolling(roll, min_periods=roll).mean()) / spread.rolling(
        roll, min_periods=roll
    ).std().replace(0, np.nan)
    z_clean = z.dropna()
    z_span = float(z_clean.max() - z_clean.min()) if len(z_clean) else 0.0
    straight = line_r2 * (1.0 - min(drift_ratio, 0.85))
    channel_score = spread_range * straight * max(corr, 0.0) * max(line_r2, 0.0)
    return {
        "spread_range": round(spread_range, 2),
        "spread_std": round(spread_std, 2),
        "spread_min": round(float(spread.min()), 2),
        "spread_max": round(float(spread.max()), 2),
        "drift_ratio": round(drift_ratio, 4),
        "line_r2": round(line_r2, 4),
        "correlation": round(corr, 4),
        "z_span": round(z_span, 2),
        "channel_score": round(channel_score, 2),
    }


def channel_bounds(spread: pd.Series, lower_pct: float = 12.0, upper_pct: float = 88.0) -> Tuple[float, float, float]:
    """Fixed straight channel: lower / mid / upper from spread percentiles."""
    lo = float(spread.quantile(lower_pct / 100.0))
    hi = float(spread.quantile(upper_pct / 100.0))
    mid = float(spread.quantile(0.5))
    return lo, mid, hi


def hedged_levels(level_a: pd.Series, level_b: pd.Series) -> Tuple[pd.Series, pd.Series, float]:
    """OLS hedge ratio so spread channel is flatter (straight pair line)."""
    level_a, level_b = _align_levels(level_a, level_b)
    if len(level_a) < 20:
        return level_a, level_b, 1.0
    var_b = float(np.var(level_b.values))
    if var_b <= 0:
        return level_a, level_b, 1.0
    beta = float(np.cov(level_a.values, level_b.values)[0, 1] / var_b)
    # Express as two indices both ~10k: A unchanged, B scaled to hedged synthetic
    hedged_b = level_b * beta
    return level_a, hedged_b, beta


def channel_roundtrip_trades(
    level_a: pd.Series,
    level_b: pd.Series,
    lower_pct: float = 32.0,
    upper_pct: float = 68.0,
    use_hedge: bool = True,
) -> Dict:
    """
    Buy spread at lower channel (long A, short B), sell at upper channel.
    Simple buy → sell → buy → sell rhythm.
    """
    level_a, level_b = _align_levels(level_a, level_b)
    beta = 1.0
    if use_hedge:
        level_a, level_b, beta = hedged_levels(level_a, level_b)
    spread = level_a - level_b
    lo, mid, hi = channel_bounds(spread, lower_pct, upper_pct)
    ret_a = level_a.pct_change().fillna(0.0)
    ret_b = level_b.pct_change().fillna(0.0)
    spread_ret = ret_a - (beta * ret_b if use_hedge else ret_b)

    position = 0  # 1 = long spread
    trades = []
    equity = [0.0]
    for i in range(1, len(spread)):
        s = float(spread.iloc[i])
        pnl_bar = 0.0
        if position == 1:
            pnl_bar = float(spread_ret.iloc[i] * 100)
        if position == 0 and s <= lo:
            position = 1
            trades.append({"bar": i, "action": "BUY_SPREAD", "spread": s, "level_a": float(level_a.iloc[i])})
        elif position == 1 and s >= hi:
            position = 0
            trades.append({"bar": i, "action": "SELL_SPREAD", "spread": s, "level_a": float(level_a.iloc[i])})
        equity.append(equity[-1] + pnl_bar)

    eq = pd.Series(equity[1:], index=level_a.index[1:])
    peak = eq.cummax()
    max_dd = float((peak - eq).max())
    roundtrips = sum(1 for t in trades if t["action"] == "SELL_SPREAD")
    return {
        "hedge_ratio": round(beta, 4),
        "channel_lower": round(lo, 2),
        "channel_mid": round(mid, 2),
        "channel_upper": round(hi, 2),
        "channel_width": round(hi - lo, 2),
        "roundtrips": roundtrips,
        "signals": trades,
        "pnl_pct": round(float(eq.iloc[-1]) if len(eq) else 0.0, 2),
        "max_dd_pct": round(max_dd, 2),
    }


def build_channel_pair(
    pool: List[StockMeta],
    prices: pd.DataFrame,
    *,
    n_per_side: int = 6,
    iterations: int = 600,
    seed: int = 42,
) -> Tuple[List[StockMeta], List[StockMeta], Dict]:
    """Pick n_per_side stocks per index to maximise straight-channel spread range."""
    random.seed(seed)
    np.random.seed(seed)
    available = [s for s in pool if s.symbol in prices.columns]
    if len(available) < n_per_side * 2 + 4:
        raise ValueError("not enough priced symbols in pool")

    best_a: List[StockMeta] = []
    best_b: List[StockMeta] = []
    best_meta: Dict = {"channel_score": -1.0}

    for _ in range(iterations):
        pick = random.sample(available, n_per_side * 2)
        a = pick[:n_per_side]
        b = pick[n_per_side:]
        if _imbalance(a, b, channel=True) > 0.55:
            continue
        la = cap_weighted_series(a, prices)
        lb = cap_weighted_series(b, prices)
        if la.empty or lb.empty:
            continue
        cm = channel_metrics(la, lb)
        if cm.get("correlation", 0) < MIN_CHANNEL_CORR:
            continue
        if cm.get("line_r2", 0) < MIN_CHANNEL_R2:
            continue
        if cm["channel_score"] > best_meta.get("channel_score", -1):
            best_a, best_b = a, b
            best_meta = cm

    if not best_a:
        # seeded search: split each sector's top caps across A/B
        groups = _sector_groups(available)
        a, b = [], []
        for _sec, stocks in sorted(groups.items()):
            for i, s in enumerate(stocks[:4]):
                (a if i % 2 == 0 else b).append(s)
        a = a[:n_per_side]
        b = b[:n_per_side]
        while len(a) < n_per_side:
            for s in available:
                if s not in a and s not in b:
                    a.append(s)
                    break
        while len(b) < n_per_side:
            for s in available:
                if s not in a and s not in b:
                    b.append(s)
                    break
        for _ in range(200):
            if not a or not b:
                break
            ia, ib = random.randrange(len(a)), random.randrange(len(b))
            a[ia], b[ib] = b[ib], a[ia]
            la = cap_weighted_series(a, prices)
            lb = cap_weighted_series(b, prices)
            cm = channel_metrics(la, lb)
            if cm.get("correlation", 0) >= MIN_CHANNEL_CORR and cm.get("line_r2", 0) >= MIN_CHANNEL_R2:
                if cm["channel_score"] > best_meta.get("channel_score", -1):
                    best_a, best_b = list(a), list(b)
                    best_meta = cm
            else:
                a[ia], b[ib] = b[ib], a[ia]
        if not best_a:
            best_a, best_b = a[:n_per_side], b[:n_per_side]

    la = cap_weighted_series(best_a, prices)
    lb = cap_weighted_series(best_b, prices)
    best_meta = channel_metrics(la, lb)
    return best_a, best_b, best_meta


def build_pair_indices_channel(
    pool: List[StockMeta],
    prices: pd.DataFrame,
    code_a: str = "A10",
    code_b: str = "B12",
    n_per_side: int = 6,
) -> PairBuildResult:
    a_list, b_list, ch = build_channel_pair(pool, prices, n_per_side=n_per_side)
    idx_a = SyntheticIndex(code=code_a, name=f"Channel {code_a}", members=a_list)
    idx_b = SyntheticIndex(code=code_b, name=f"Channel {code_b}", members=b_list)
    ta, tb = idx_a.totals(), idx_b.totals()
    balance = {
        "A10": {**ta, "n": idx_a.n, "sectors": idx_a.sector_weights()},
        "B12": {**tb, "n": idx_b.n, "sectors": idx_b.sector_weights()},
        "ratios": {
            "cap_a_over_b": round(ta["market_cap"] / max(tb["market_cap"], 1), 4),
            "price_a_over_b": round(ta["price_sum"] / max(tb["price_sum"], 1), 4),
            "volume_a_over_b": round(ta["volume"] / max(tb["volume"], 1), 4),
        },
        "channel": ch,
    }
    return PairBuildResult(
        index_a=idx_a,
        index_b=idx_b,
        pool_size=len(pool),
        valid_pool=len(pool),
        balance=balance,
    )


def fetch_pool_history(
    symbols: List[str],
    months: int = 2,
    interval: str = "1h",
    chunk: int = 40,
) -> pd.DataFrame:
    """Batch-download OHLCV close matrix for the full pool."""
    from datetime import datetime, timedelta, timezone

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=months * 31)
    frames: List[pd.Series] = []
    for i in range(0, len(symbols), chunk):
        chunk_syms = symbols[i : i + chunk]
        for sym in chunk_syms:
            df = yf.download(
                sym,
                start=start.strftime("%Y-%m-%d"),
                end=end.strftime("%Y-%m-%d"),
                interval=interval,
                progress=False,
                auto_adjust=True,
                threads=False,
            )
            if df is None or df.empty:
                continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            frames.append(df["Close"].rename(sym))
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, axis=1).sort_index().ffill()


def backtest_pair(
    level_a: pd.Series,
    level_b: pd.Series,
    z_entry: float = 2.0,
    z_exit: float = 0.5,
) -> Dict:
    """Spread z-score mean-reversion pair stats."""
    level_a, level_b = _align_levels(level_a, level_b)
    spread = level_a - level_b
    ratio = level_a / level_b
    roll = min(48, max(12, len(spread) // 10))
    mu = spread.rolling(roll, min_periods=roll).mean()
    sd = spread.rolling(roll, min_periods=roll).std()
    z = (spread - mu) / sd.replace(0, np.nan)

    ret_a = level_a.pct_change()
    ret_b = level_b.pct_change()
    corr = ret_a.corr(ret_b)

    # Simple pair trade on z-score
    position = 0  # +1 long spread (long A short B)
    pnl = []
    for i in range(1, len(z)):
        zi = z.iloc[i]
        if np.isnan(zi):
            pnl.append(0.0)
            continue
        if position == 0:
            if zi > z_entry:
                position = -1
            elif zi < -z_entry:
                position = 1
        else:
            if abs(zi) < z_exit:
                position = 0
        if position == 1:
            pnl.append((ret_a.iloc[i] - ret_b.iloc[i]) * 100)
        elif position == -1:
            pnl.append((ret_b.iloc[i] - ret_a.iloc[i]) * 100)
        else:
            pnl.append(0.0)

    pnl_s = pd.Series(pnl, index=level_a.index[1:])
    equity = pnl_s.cumsum()
    peak = equity.cummax()
    dd = (peak - equity).max()

    return {
        "correlation": round(float(corr), 4) if not np.isnan(corr) else 0.0,
        "spread_mean": round(float(spread.mean()), 2),
        "spread_std": round(float(spread.std()), 2),
        "spread_min": round(float(spread.min()), 2),
        "spread_max": round(float(spread.max()), 2),
        "ratio_mean": round(float(ratio.mean()), 4),
        "ratio_std": round(float(ratio.std()), 4),
        "z_min": round(float(z.min()), 2),
        "z_max": round(float(z.max()), 2),
        "pair_trades_pnl_pct": round(float(pnl_s.sum()), 2),
        "pair_max_dd_pct": round(float(dd), 2),
        "bars": len(level_a),
    }


def save_config(result: PairBuildResult, path: Path) -> None:
    def pack(idx: SyntheticIndex) -> dict:
        return {
            "code": idx.code,
            "name": idx.name,
            "n": idx.n,
            "target_level": INDEX_TARGET,
            "members": [
                {
                    "symbol": m.symbol,
                    "name": m.name,
                    "sector": m.sector,
                    "region": m.region,
                    "price": round(m.price, 4),
                    "market_cap": m.market_cap,
                    "weight": round(m.weight, 6),
                }
                for m in idx.members
            ],
            "totals": idx.totals(),
            "sector_weights": {k: round(v, 4) for k, v in idx.sector_weights().items()},
        }

    payload = {
        "pair": "A10_B12",
        "index_target": INDEX_TARGET,
        "A10": pack(result.index_a),
        "B12": pack(result.index_b),
        "balance": result.balance,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
