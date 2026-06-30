"""
Backtester для WTI (Crude Oil) H4 - PREMIUM сигналы за год.
Тестирует улучшенную модель качества сигнала с confluence-фильтрами.
"""

import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta

import yfinance as yf

from src.signal_strength import SignalStrengthAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WTIH4PremiumBacktester:
    def __init__(self):
        self.signal_analyzer = SignalStrengthAnalyzer()
        self.min_quality_score = 70
        self.loss_streak_limit = 2
        self.results = {
            'raw_candidates': 0,
            'filtered_out_signals': 0,
            'signal_reduction_pct': 0,
            'total_premium_signals': 0,
            'winning_signals': 0,
            'losing_signals': 0,
            'win_rate': 0,
            'signals_detail': [],
            'monthly_stats': {},
            'quality_tiers': {},
            'best_month': None,
            'worst_month': None,
            'avg_winning_pnl': 0,
            'max_drawdown_recovery_signals': 0
        }

    def download_wti_data(self, days=365):
        """Скачать данные WTI за последний год."""
        logger.info(f"�� Загружаю WTI данные H4 за {days} дней...")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        try:
            df = yf.download('CL=F', start=start_date, end=end_date, interval='4h', progress=False)
            logger.info(f"✅ Загружено {len(df)} свечей H4")
            return df
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки: {e}")
            return None

    def calculate_rsi(self, df, period=14):
        """Расчёт RSI."""
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def _quality_tier(self, quality_score):
        if quality_score >= 90:
            return '90-100'
        if quality_score >= 80:
            return '80-89'
        return '70-79'

    def detect_premium_divergence(self, df):
        """Обнаруживает только высококачественные PREMIUM сигналы."""
        if df is None or df.empty:
            return [], df

        signals = []
        raw_candidates = 0

        for i in range(40, len(df) - 1):
            window = df.iloc[:i + 1].copy()
            analysis = self.signal_analyzer.analyze(
                'WTI',
                window['Close'],
                self.calculate_rsi(window),
                window['Volume'],
                market_data=window
            )

            if analysis is None or analysis.divergence_bias == 'NONE':
                continue

            raw_candidates += 1

            if not analysis.premium_entry or analysis.quality_score < self.min_quality_score:
                continue

            signals.append({
                'date': window.index[-1],
                'price': float(window['Close'].iloc[-1]),
                'rsi': analysis.rsi_value,
                'type': analysis.divergence_bias,
                'index': i,
                'factors': analysis.factors_count,
                'confidence': float(analysis.confidence * 100),
                'quality_score': analysis.quality_score,
                'risk_reward_ratio': analysis.risk_reward_ratio,
                'adx_value': analysis.adx_value
            })

        self.results['raw_candidates'] = raw_candidates
        self.results['filtered_out_signals'] = max(raw_candidates - len(signals), 0)
        self.results['signal_reduction_pct'] = round(
            (self.results['filtered_out_signals'] / raw_candidates * 100) if raw_candidates else 0,
            2
        )
        return signals, df

    def check_signal_profitability(self, df, signal, lookforward=6):
        """Проверяет был ли сигнал прибыльным за 24 часа (6 свечей H4)."""
        signal_idx = signal['index']
        future_idx_start = min(signal_idx + 1, len(df) - 1)
        future_idx_end = min(signal_idx + lookforward, len(df) - 1)

        if future_idx_end <= future_idx_start:
            return None, None, None

        future_prices = df['Close'].iloc[future_idx_start:future_idx_end]

        if signal['type'] == 'BEARISH':
            min_price = future_prices.min()
            profit = signal['price'] - min_price
            is_profitable = profit > 0.05
        else:
            max_price = future_prices.max()
            profit = max_price - signal['price']
            is_profitable = profit > 0.05

        return is_profitable, profit, future_prices.iloc[-1] if len(future_prices) > 0 else None

    def _calculate_recovery_signals(self, pnl_series):
        peak = 0.0
        running = 0.0
        recovery = 0
        max_recovery = 0
        in_drawdown = False

        for pnl in pnl_series:
            running += pnl
            if running >= peak:
                peak = running
                if in_drawdown:
                    max_recovery = max(max_recovery, recovery)
                    recovery = 0
                    in_drawdown = False
            else:
                in_drawdown = True
                recovery += 1

        if in_drawdown:
            max_recovery = max(max_recovery, recovery)
        return max_recovery

    def backtest(self):
        """Запустить бэктест."""
        print("\n" + "=" * 100)
        print("🧪 BACKTESTING WTI (Crude Oil) H4 - PREMIUM Signals Only (1 Year)")
        print("=" * 100 + "\n")

        df = self.download_wti_data(days=365)
        if df is None or df.empty:
            print("❌ Не удалось загрузить данные или данные пустые!")
            return None

        print(f"📊 Данные H4: {df.index[0].date()} → {df.index[-1].date()}")
        print(f"📈 Диапазон цен: ${df['Close'].min():.2f} - ${df['Close'].max():.2f}\n")

        signals, df_analyzed = self.detect_premium_divergence(df)

        print(f"🔍 Исходных дивергентных сетапов: {self.results['raw_candidates']}")
        print(f"✅ PREMIUM сигналов после фильтрации: {len(signals)}")
        print(f"🛡️ Сокращение сигналов: {self.results['signal_reduction_pct']:.1f}%\n")

        if len(signals) == 0:
            print("⚠️ PREMIUM сигналы не найдены!")
            return None

        signals.sort(key=lambda x: x['date'])

        print("-" * 120)
        print(f"{'Date':<20} {'Price':<10} {'RSI':<8} {'Type':<10} {'Score':<8} {'RR':<8} {'ADX':<8} {'Profitable':<12} {'P/L ($)':<12}")
        print("-" * 120)

        winning = 0
        losing = 0
        total_pnl = 0.0
        winning_pnl = 0.0
        pnl_series = []
        monthly_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'pnl': 0.0, 'count': 0})
        quality_tiers = defaultdict(lambda: {'wins': 0, 'losses': 0, 'pnl': 0.0, 'count': 0})
        loss_streaks = {'BULLISH': 0, 'BEARISH': 0}
        skipped_after_losses = 0

        for signal in signals:
            if loss_streaks[signal['type']] >= self.loss_streak_limit:
                skipped_after_losses += 1
                continue

            is_profitable, profit, _ = self.check_signal_profitability(df_analyzed, signal)
            if is_profitable is None:
                continue

            status = "✅ WIN" if is_profitable else "❌ LOSS"
            winning += int(is_profitable)
            losing += int(not is_profitable)
            total_pnl += float(profit)
            pnl_series.append(float(profit))

            if is_profitable:
                winning_pnl += float(profit)
                loss_streaks[signal['type']] = 0
            else:
                loss_streaks[signal['type']] += 1

            month_key = signal['date'].strftime('%Y-%m')
            monthly_stats[month_key]['count'] += 1
            monthly_stats[month_key]['wins'] += int(is_profitable)
            monthly_stats[month_key]['losses'] += int(not is_profitable)
            monthly_stats[month_key]['pnl'] += float(profit)

            tier = self._quality_tier(signal['quality_score'])
            quality_tiers[tier]['count'] += 1
            quality_tiers[tier]['wins'] += int(is_profitable)
            quality_tiers[tier]['losses'] += int(not is_profitable)
            quality_tiers[tier]['pnl'] += float(profit)

            signal_date = signal['date'].strftime('%Y-%m-%d %H:%M')
            print(f"{signal_date:<20} ${signal['price']:<9.2f} {signal['rsi']:<8.1f} {signal['type']:<10} {signal['quality_score']:<8} {signal['risk_reward_ratio']:<8.2f} {signal['adx_value']:<8.1f} {status:<12} ${profit:<11.4f}")

            self.results['signals_detail'].append({
                'date': signal_date,
                'price': signal['price'],
                'rsi': float(signal['rsi']),
                'type': signal['type'],
                'factors': signal['factors'],
                'confidence': float(signal['confidence']),
                'quality_score': signal['quality_score'],
                'risk_reward_ratio': float(signal['risk_reward_ratio']),
                'adx_value': float(signal['adx_value']),
                'profitable': bool(is_profitable),
                'profit_loss': float(profit)
            })

        print("-" * 120)

        total_tested = winning + losing
        win_rate = (winning / total_tested * 100) if total_tested > 0 else 0

        self.results['total_premium_signals'] = len(signals)
        self.results['tested_signals'] = total_tested
        self.results['skipped_after_loss_limit'] = skipped_after_losses
        self.results['winning_signals'] = winning
        self.results['losing_signals'] = losing
        self.results['win_rate'] = round(win_rate, 2)
        self.results['total_pnl'] = round(total_pnl, 4)
        self.results['avg_pnl_per_signal'] = round(total_pnl / total_tested, 4) if total_tested > 0 else 0
        self.results['avg_winning_pnl'] = round(winning_pnl / winning, 4) if winning > 0 else 0
        self.results['max_drawdown_recovery_signals'] = self._calculate_recovery_signals(pnl_series)

        best_month = None
        worst_month = None
        best_pnl = float('-inf')
        worst_pnl = float('inf')

        for month, stats in sorted(monthly_stats.items()):
            if stats['pnl'] > best_pnl:
                best_pnl = stats['pnl']
                best_month = month
            if stats['pnl'] < worst_pnl:
                worst_pnl = stats['pnl']
                worst_month = month
            self.results['monthly_stats'][month] = {
                'signals': stats['count'],
                'wins': stats['wins'],
                'losses': stats['losses'],
                'win_rate': round((stats['wins'] / stats['count'] * 100) if stats['count'] > 0 else 0, 1),
                'pnl': round(stats['pnl'], 4)
            }

        for tier, stats in sorted(quality_tiers.items()):
            self.results['quality_tiers'][tier] = {
                'signals': stats['count'],
                'wins': stats['wins'],
                'losses': stats['losses'],
                'win_rate': round((stats['wins'] / stats['count'] * 100) if stats['count'] > 0 else 0, 1),
                'pnl': round(stats['pnl'], 4)
            }

        self.results['best_month'] = best_month
        self.results['worst_month'] = worst_month

        print("\n" + "=" * 100)
        print("📊 ИТОГОВЫЕ РЕЗУЛЬТАТЫ - WTI PREMIUM SIGNALS ONLY")
        print("=" * 100)
        print(f"✅ Выигрышных PREMIUM сигналов:     {winning}")
        print(f"❌ Проигрышных PREMIUM сигналов:    {losing}")
        print(f"📈 Win Rate (PREMIUM):              {win_rate:.1f}%")
        print(f"💰 Общий P/L за год ($):            ${total_pnl:.4f}")
        print(f"📍 Средний P/L на сигнал:           ${self.results['avg_pnl_per_signal']:.4f}")
        print(f"🏆 Средний P/L на WIN:              ${self.results['avg_winning_pnl']:.4f}")
        print(f"🛡️ Пропущено после 2 убытков:       {skipped_after_losses}")
        print(f"📉 Recovery после drawdown:         {self.results['max_drawdown_recovery_signals']} сигналов")
        print("=" * 100 + "\n")

        print("📅 МЕСЯЧНАЯ СТАТИСТИКА WTI")
        print("-" * 100)
        print(f"{'Month':<12} {'Signals':<10} {'Wins':<8} {'Losses':<8} {'Win Rate':<12} {'P/L ($)':<12}")
        print("-" * 100)
        for month in sorted(monthly_stats.keys()):
            stats = self.results['monthly_stats'][month]
            print(f"{month:<12} {stats['signals']:<10} {stats['wins']:<8} {stats['losses']:<8} {stats['win_rate']:<12}% ${stats['pnl']:<11.4f}")

        print("-" * 100)
        print(f"🏆 Лучший месяц:  {best_month} (P/L: ${best_pnl:.4f})")
        print(f"📉 Худший месяц:  {worst_month} (P/L: ${worst_pnl:.4f})")
        print("=" * 100 + "\n")

        print("📊 WIN RATE ПО QUALITY TIER")
        print("-" * 80)
        print(f"{'Tier':<10} {'Signals':<10} {'Wins':<8} {'Losses':<8} {'Win Rate':<12} {'P/L':<12}")
        print("-" * 80)
        for tier in sorted(self.results['quality_tiers'].keys()):
            stats = self.results['quality_tiers'][tier]
            print(f"{tier:<10} {stats['signals']:<10} {stats['wins']:<8} {stats['losses']:<8} {stats['win_rate']:<12}% {stats['pnl']:<12.4f}")
        print("-" * 80)

        self.save_results()
        return self.results

    def save_results(self):
        """Сохранить результаты в JSON."""
        with open('backtest_wti_h4_premium_results.json', 'w') as f:
            json.dump(self.results, f, indent=2)
        logger.info("💾 Результаты сохранены в backtest_wti_h4_premium_results.json")


if __name__ == '__main__':
    backtester = WTIH4PremiumBacktester()
    backtester.backtest()
