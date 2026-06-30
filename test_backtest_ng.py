"""
Backtester для NG (Natural Gas) - RSI Divergence Strategy
Тестирует стратегию на исторических данных за последний месяц
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NGBacktester:
    def __init__(self):
        self.signals = []
        self.results = {
            'total_signals': 0,
            'winning_signals': 0,
            'losing_signals': 0,
            'win_rate': 0,
            'signals_detail': []
        }
    
    def download_ng_data(self, days=30):
        """Скачать данные NG за последний месяц"""
        logger.info(f"📥 Загружаю NG данные за {days} дней...")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        try:
            # Используем yfinance для загрузки
            df = yf.download('NG=F', start=start_date, end=end_date, interval='1h', progress=False)
            logger.info(f"✅ Загружено {len(df)} свечей")
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
    
    def detect_divergence(self, df):
        """Обнаруживает RSI дивергенции"""
        df['RSI'] = self.calculate_rsi(df)
        df['MACD'], df['MACD_signal'], df['MACD_hist'] = self.calculate_macd(df)
        
        signals = []
        
        for i in range(2, len(df)-1):
            # Проверяем на BEARISH дивергенцию (цена выше, RSI ниже)
            if (df['Close'].iloc[i] > df['Close'].iloc[i-2] and 
                df['RSI'].iloc[i] < df['RSI'].iloc[i-2] and
                df['RSI'].iloc[i] > 70):  # Oversold условие
                
                signals.append({
                    'date': df.index[i],
                    'price': df['Close'].iloc[i],
                    'rsi': df['RSI'].iloc[i],
                    'type': 'BEARISH',
                    'index': i
                })
            
            # Проверяем на BULLISH дивергенцию (цена ниже, RSI выше)
            elif (df['Close'].iloc[i] < df['Close'].iloc[i-2] and 
                  df['RSI'].iloc[i] > df['RSI'].iloc[i-2] and
                  df['RSI'].iloc[i] < 30):  # Oversold условие
                
                signals.append({
                    'date': df.index[i],
                    'price': df['Close'].iloc[i],
                    'rsi': df['RSI'].iloc[i],
                    'type': 'BULLISH',
                    'index': i
                })
        
        return signals, df
    
    def check_signal_profitability(self, df, signal, lookforward=24):
        """Проверяет был ли сигнал прибыльным (за 24 часа вперёд)"""
        signal_idx = signal['index']
        
        # Берём цену за 24 часа после сигнала
        future_idx_start = min(signal_idx + 1, len(df) - 1)
        future_idx_end = min(signal_idx + lookforward, len(df) - 1)
        
        if future_idx_end <= future_idx_start:
            return None, None, None
        
        future_prices = df['Close'].iloc[future_idx_start:future_idx_end]
        
        if signal['type'] == 'BEARISH':
            # Для bearish сигнала ожидаем падение
            min_price = future_prices.min()
            profit = signal['price'] - min_price
            is_profitable = profit > 0
            
        else:  # BULLISH
            # Для bullish сигнала ожидаем рост
            max_price = future_prices.max()
            profit = max_price - signal['price']
            is_profitable = profit > 0
        
        return is_profitable, profit, future_prices.iloc[-1] if len(future_prices) > 0 else None
    
    def backtest(self):
        """Запустить бэктест"""
        print("\n" + "="*80)
        print("🧪 BACKTESTING NG (Natural Gas) - RSI Divergence Strategy")
        print("="*80 + "\n")
        
        # Загружаем данные
        df = self.download_ng_data(days=30)
        if df is None:
            print("❌ Не удалось загрузить данные!")
            return
        
        print(f"📊 Данные: {df.index[0]} → {df.index[-1]}")
        print(f"📈 Диапазон цен: {df['Close'].min():.2f} - {df['Close'].max():.2f}\n")
        
        # Обнаруживаем дивергенции
        signals, df_analyzed = self.detect_divergence(df)
        
        print(f"🔍 Найдено сигналов: {len(signals)}\n")
        
        if len(signals) == 0:
            print("⚠️ Сигналы не найдены!")
            return
        
        # Проверяем каждый сигнал
        print("-" * 80)
        print(f"{'Date':<20} {'Price':<10} {'RSI':<8} {'Type':<10} {'Profitable':<12} {'P/L (pts)':<12}")
        print("-" * 80)
        
        winning = 0
        losing = 0
        total_pnl = 0
        
        for signal in signals:
            is_profitable, profit, price_after = self.check_signal_profitability(df_analyzed, signal)
            
            if is_profitable is not None:
                status = "✅ WIN" if is_profitable else "❌ LOSS"
                winning += is_profitable
                losing += not is_profitable
                
                if profit is not None:
                    total_pnl += profit
                
                signal_date = signal['date'].strftime('%Y-%m-%d %H:%M')
                print(f"{signal_date:<20} {signal['price']:<10.2f} {signal['rsi']:<8.1f} {signal['type']:<10} {status:<12} {profit:<12.4f}")
                
                self.results['signals_detail'].append({
                    'date': signal_date,
                    'price': float(signal['price']),
                    'rsi': float(signal['rsi']),
                    'type': signal['type'],
                    'profitable': is_profitable,
                    'profit_loss': float(profit) if profit else 0
                })
        
        print("-" * 80)
        
        # Рассчитываем статистику
        total_tested = winning + losing
        win_rate = (winning / total_tested * 100) if total_tested > 0 else 0
        
        self.results['total_signals'] = len(signals)
        self.results['tested_signals'] = total_tested
        self.results['winning_signals'] = winning
        self.results['losing_signals'] = losing
        self.results['win_rate'] = round(win_rate, 2)
        self.results['total_pnl'] = round(total_pnl, 4)
        self.results['avg_pnl_per_signal'] = round(total_pnl / total_tested, 4) if total_tested > 0 else 0
        
        # Выводим результаты
        print("\n" + "="*80)
        print("📊 ИТОГОВЫЕ РЕЗУЛЬТАТЫ")
        print("="*80)
        print(f"✅ Выигрышных сигналов:     {winning}")
        print(f"❌ Проигрышных сигналов:    {losing}")
        print(f"📈 Win Rate:                {win_rate:.1f}%")
        print(f"💰 Общий P/L (points):      {total_pnl:.4f}")
        print(f"📍 Средний P/L на сигнал:   {self.results['avg_pnl_per_signal']:.4f}")
        print("="*80 + "\n")
        
        # Сохраняем результаты
        self.save_results()
        
        return self.results
    
    def save_results(self):
        """Сохранить результаты в JSON"""
        with open('backtest_ng_results.json', 'w') as f:
            json.dump(self.results, f, indent=2)
        logger.info("💾 Результаты сохранены в backtest_ng_results.json")


if __name__ == '__main__':
    backtester = NGBacktester()
    backtester.backtest()
