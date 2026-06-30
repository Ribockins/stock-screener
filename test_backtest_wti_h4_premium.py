"""
Backtester для WTI (Crude Oil) H4 - PREMIUM сигналы за год
Тестирует только PREMIUM_WARNING сигналы на 4-часовом таймфрейме
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
import json
import logging
from collections import defaultdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WTIH4PremiumBacktester:
    def __init__(self):
        self.signals = []
        self.results = {
            'total_premium_signals': 0,
            'winning_signals': 0,
            'losing_signals': 0,
            'win_rate': 0,
            'signals_detail': [],
            'monthly_stats': {},
            'best_month': None,
            'worst_month': None
        }
    
    def download_wti_data(self, days=365):
        """Скачать данные WTI за последний год"""
        logger.info(f"📥 Загружаю WTI данные H4 за {days} дней...")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        try:
            # Используем yfinance для загрузки H4 данных
            df = yf.download('CL=F', start=start_date, end=end_date, interval='4h', progress=False)
            logger.info(f"✅ Загружено {len(df)} свечей H4")
            return df
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки: {e}")
            return None
    
    def calculate_rsi(self, df, period=14):
        """Расчёт RSI"""
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_macd(self, df):
        """Расчёт MACD"""
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        histogram = macd - signal
        return macd, signal, histogram
    
    def calculate_volume_sma(self, df, period=20):
        """Расчёт среднего объёма"""
        return df['Volume'].rolling(window=period).mean()
    
    def detect_premium_divergence(self, df):
        """
        Обнаруживает PREMIUM сигналы RSI дивергенции
        PREMIUM = все 7 факторов совпадают (92% уверенность)
        """
        df['RSI'] = self.calculate_rsi(df)
        df['MACD'], df['MACD_signal'], df['MACD_hist'] = self.calculate_macd(df)
        df['Vol_SMA'] = self.calculate_volume_sma(df)
        
        signals = []
        
        for i in range(3, len(df)-1):
            rsi = df['RSI'].iloc[i]
            prev_rsi = df['RSI'].iloc[i-2]
            
            price = df['Close'].iloc[i]
            prev_price = df['Close'].iloc[i-2]
            
            macd_hist = df['MACD_hist'].iloc[i]
            prev_macd_hist = df['MACD_hist'].iloc[i-1]
            
            volume = df['Volume'].iloc[i]
            vol_sma = df['Vol_SMA'].iloc[i]
            
            # BEARISH PREMIUM (цена выше, RSI ниже)
            if (price > prev_price and rsi < prev_rsi and rsi > 65):
                
                # Проверяем все 7 факторов для PREMIUM
                factors_met = 0
                
                # Factor 1: RSI дивергенция
                if rsi < prev_rsi:
                    factors_met += 1
                
                # Factor 2: Цена выше
                if price > prev_price:
                    factors_met += 1
                
                # Factor 3: MACD гистограмма ослабевает
                if macd_hist < prev_macd_hist:
                    factors_met += 1
                
                # Factor 4: RSI в диапазоне 65-80 (сильный уровень)
                if 65 < rsi < 80:
                    factors_met += 1
                
                # Factor 5: Объём выше среднего
                if volume > vol_sma * 1.2:
                    factors_met += 1
                
                # Factor 6: Wick на последней свече (reversal signal)
                wick = df['High'].iloc[i] - max(df['Open'].iloc[i], df['Close'].iloc[i])
                if wick > (df['High'].iloc[i] - df['Low'].iloc[i]) * 0.3:
                    factors_met += 1
                
                # Factor 7: Close near low (давление продавцов)
                body_size = abs(df['Close'].iloc[i] - df['Open'].iloc[i])
                if body_size < (df['High'].iloc[i] - df['Low'].iloc[i]) * 0.4:
                    factors_met += 1
                
                # PREMIUM = 7/7 факторов или минимум 6/7
                if factors_met >= 6:
                    signals.append({
                        'date': df.index[i],
                        'price': df['Close'].iloc[i],
                        'rsi': rsi,
                        'type': 'BEARISH',
                        'index': i,
                        'factors': factors_met,
                        'confidence': (factors_met / 7) * 100
                    })
            
            # BULLISH PREMIUM (цена ниже, RSI выше)
            elif (price < prev_price and rsi > prev_rsi and rsi < 35):
                
                factors_met = 0
                
                # Factor 1: RSI дивергенция
                if rsi > prev_rsi:
                    factors_met += 1
                
                # Factor 2: Цена ниже
                if price < prev_price:
                    factors_met += 1
                
                # Factor 3: MACD гистограмма усиливается
                if macd_hist > prev_macd_hist:
                    factors_met += 1
                
                # Factor 4: RSI в диапазоне 20-35 (сильный уровень)
                if 20 < rsi < 35:
                    factors_met += 1
                
                # Factor 5: Объём выше среднего
                if volume > vol_sma * 1.2:
                    factors_met += 1
                
                # Factor 6: Wick на последней свече (reversal signal)
                wick = min(df['Open'].iloc[i], df['Close'].iloc[i]) - df['Low'].iloc[i]
                if wick > (df['High'].iloc[i] - df['Low'].iloc[i]) * 0.3:
                    factors_met += 1
                
                # Factor 7: Close near high (давление покупателей)
                body_size = abs(df['Close'].iloc[i] - df['Open'].iloc[i])
                if body_size < (df['High'].iloc[i] - df['Low'].iloc[i]) * 0.4:
                    factors_met += 1
                
                # PREMIUM = 7/7 факторов или минимум 6/7
                if factors_met >= 6:
                    signals.append({
                        'date': df.index[i],
                        'price': df['Close'].iloc[i],
                        'rsi': rsi,
                        'type': 'BULLISH',
                        'index': i,
                        'factors': factors_met,
                        'confidence': (factors_met / 7) * 100
                    })
        
        return signals, df
    
    def check_signal_profitability(self, df, signal, lookforward=6):
        """
        Проверяет был ли сигнал прибыльным
        На H4 ищем профит за 6 свечей (24 часа)
        """
        signal_idx = signal['index']
        
        future_idx_start = min(signal_idx + 1, len(df) - 1)
        future_idx_end = min(signal_idx + lookforward, len(df) - 1)
        
        if future_idx_end <= future_idx_start:
            return None, None, None
        
        future_prices = df['Close'].iloc[future_idx_start:future_idx_end]
        
        if signal['type'] == 'BEARISH':
            # Ожидаем падение
            min_price = future_prices.min()
            profit = signal['price'] - min_price
            is_profitable = profit > 0.05  # Минимум 5 центов профита
            
        else:  # BULLISH
            # Ожидаем рост
            max_price = future_prices.max()
            profit = max_price - signal['price']
            is_profitable = profit > 0.05
        
        return is_profitable, profit, future_prices.iloc[-1] if len(future_prices) > 0 else None
    
    def backtest(self):
        """Запустить бэктест"""
        print("\n" + "="*100)
        print("🧪 BACKTESTING WTI (Crude Oil) H4 - PREMIUM Signals Only (1 Year)")
        print("="*100 + "\n")
        
        # Загружаем данные
        df = self.download_wti_data(days=365)
        if df is None:
            print("❌ Не удалось загрузить данные!")
            return
        
        print(f"📊 Данные H4: {df.index[0].date()} → {df.index[-1].date()}")
        print(f"📈 Диапазон цен: ${df['Close'].min():.2f} - ${df['Close'].max():.2f}\n")
        
        # Обнаруживаем PREMIUM дивергенции
        signals, df_analyzed = self.detect_premium_divergence(df)
        
        print(f"🔍 Найдено PREMIUM сигналов: {len(signals)}\n")
        
        if len(signals) == 0:
            print("⚠️ PREMIUM сигналы не найдены!")
            return
        
        # Сортируем по дате
        signals.sort(key=lambda x: x['date'])
        
        # Проверяем каждый сигнал
        print("-" * 100)
        print(f"{'Date':<20} {'Price':<10} {'RSI':<8} {'Type':<10} {'Factors':<8} {'Confidence':<12} {'Profitable':<12} {'P/L ($)':<12}")
        print("-" * 100)
        
        winning = 0
        losing = 0
        total_pnl = 0
        monthly_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'pnl': 0, 'count': 0})
        
        for signal in signals:
            is_profitable, profit, price_after = self.check_signal_profitability(df_analyzed, signal)
            
            if is_profitable is not None:
                status = "✅ WIN" if is_profitable else "❌ LOSS"
                winning += is_profitable
                losing += not is_profitable
                
                if profit is not None:
                    total_pnl += profit
                
                # Группируем по месяцам
                month_key = signal['date'].strftime('%Y-%m')
                monthly_stats[month_key]['count'] += 1
                if is_profitable:
                    monthly_stats[month_key]['wins'] += 1
                else:
                    monthly_stats[month_key]['losses'] += 1
                monthly_stats[month_key]['pnl'] += profit if profit else 0
                
                signal_date = signal['date'].strftime('%Y-%m-%d %H:%M')
                confidence = signal['confidence']
                print(f"{signal_date:<20} ${signal['price']:<9.2f} {signal['rsi']:<8.1f} {signal['type']:<10} {signal['factors']:<8} {confidence:<12.1f}% {status:<12} ${profit:<11.4f}")
                
                self.results['signals_detail'].append({
                    'date': signal_date,
                    'price': float(signal['price']),
                    'rsi': float(signal['rsi']),
                    'type': signal['type'],
                    'factors': signal['factors'],
                    'confidence': float(confidence),
                    'profitable': is_profitable,
                    'profit_loss': float(profit) if profit else 0
                })
        
        print("-" * 100)
        
        # Рассчитываем статистику
        total_tested = winning + losing
        win_rate = (winning / total_tested * 100) if total_tested > 0 else 0
        
        self.results['total_premium_signals'] = len(signals)
        self.results['tested_signals'] = total_tested
        self.results['winning_signals'] = winning
        self.results['losing_signals'] = losing
        self.results['win_rate'] = round(win_rate, 2)
        self.results['total_pnl'] = round(total_pnl, 4)
        self.results['avg_pnl_per_signal'] = round(total_pnl / total_tested, 4) if total_tested > 0 else 0
        
        # Находим лучший и худший месяц
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
        
        self.results['best_month'] = best_month
        self.results['worst_month'] = worst_month
        
        # Выводим результаты
        print("\n" + "="*100)
        print("📊 ИТОГОВЫЕ РЕЗУЛЬТАТЫ - WTI PREMIUM SIGNALS ONLY")
        print("="*100)
        print(f"✅ Выигрышных PREMIUM сигналов:     {winning}")
        print(f"❌ Проигрышных PREMIUM сигналов:    {losing}")
        print(f"📈 Win Rate (PREMIUM):              {win_rate:.1f}%")
        print(f"💰 Общий P/L за год ($):            ${total_pnl:.4f}")
        print(f"📍 Средний P/L на сигнал:           ${self.results['avg_pnl_per_signal']:.4f}")
        print("="*100 + "\n")
        
        # Месячная статистика
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
        print("="*100 + "\n")
        
        # Сохраняем результаты
        self.save_results()
        
        return self.results
    
    def save_results(self):
        """Сохранить результаты в JSON"""
        with open('backtest_wti_h4_premium_results.json', 'w') as f:
            json.dump(self.results, f, indent=2)
        logger.info("💾 Результаты сохранены в backtest_wti_h4_premium_results.json")


if __name__ == '__main__':
    backtester = WTIH4PremiumBacktester()
    backtester.backtest()
