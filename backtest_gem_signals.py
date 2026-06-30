"""
GEM Signals Backtesting Module
Tests RSI + Divergence + Candlestick confirmation signals on US30
Entry: Top score signals only
Risk/Reward: TP = 1x ATR, SL = 4x ATR (4:1 ratio)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GEMSignalsBacktester:
    """Backtester for GEM trading signals strategy"""
    
    def __init__(self, symbol='US30', start_date=None, end_date=None):
        """
        Initialize backtester
        
        Args:
            symbol: Trading symbol (default: US30)
            start_date: Start date for backtest (default: 1 year ago)
            end_date: End date for backtest (default: today)
        """
        self.symbol = symbol
        self.end_date = end_date or datetime.now()
        self.start_date = start_date or (self.end_date - timedelta(days=365))
        
        self.data = None
        self.signals = None
        self.trades = []
        self.equity_curve = []
        
    def fetch_data(self, interval='1h'):
        """
        Fetch OHLCV data from yfinance
        
        Args:
            interval: Timeframe ('1h' for hourly, '1d' for daily, etc.)
        """
        logger.info(f"Fetching {self.symbol} data from {self.start_date} to {self.end_date}")
        try:
            self.data = yf.download(
                self.symbol,
                start=self.start_date,
                end=self.end_date,
                interval=interval,
                progress=False
            )
            logger.info(f"Fetched {len(self.data)} bars")
            return self.data
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            return None
    
    def calculate_rsi(self, period=14):
        """Calculate RSI indicator"""
        delta = self.data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        self.data['RSI'] = 100 - (100 / (1 + rs))
        return self.data['RSI']
    
    def calculate_atr(self, period=14):
        """Calculate Average True Range"""
        high_low = self.data['High'] - self.data['Low']
        high_close = abs(self.data['High'] - self.data['Close'].shift())
        low_close = abs(self.data['Low'] - self.data['Close'].shift())
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        self.data['ATR'] = tr.rolling(period).mean()
        return self.data['ATR']
    
    def detect_divergence(self, rsi_threshold_ob=72, rsi_threshold_os=28, lookback=84):
        """
        Detect RSI divergences
        
        Args:
            rsi_threshold_ob: Overbought level
            rsi_threshold_os: Oversold level
            lookback: Lookback period for divergence detection
        """
        self.data['Divergence'] = 0  # 0: none, 1: bullish, -1: bearish
        
        for i in range(lookback, len(self.data)):
            # Bullish divergence: lower lows in price, higher lows in RSI
            if self.data['RSI'].iloc[i] < rsi_threshold_os:
                price_low = self.data['Low'].iloc[i - lookback:i].min()
                rsi_low = self.data['RSI'].iloc[i - lookback:i].min()
                
                if self.data['Low'].iloc[i] < price_low and self.data['RSI'].iloc[i] > rsi_low:
                    self.data.loc[self.data.index[i], 'Divergence'] = 1
            
            # Bearish divergence: higher highs in price, lower highs in RSI
            if self.data['RSI'].iloc[i] > rsi_threshold_ob:
                price_high = self.data['High'].iloc[i - lookback:i].max()
                rsi_high = self.data['RSI'].iloc[i - lookback:i].max()
                
                if self.data['High'].iloc[i] > price_high and self.data['RSI'].iloc[i] < rsi_high:
                    self.data.loc[self.data.index[i], 'Divergence'] = -1
        
        return self.data['Divergence']
    
    def detect_candlestick_patterns(self):
        """Detect candlestick confirmation patterns"""
        self.data['Candle_Signal'] = 0  # 0: none, 1: bullish, -1: bearish
        
        for i in range(1, len(self.data)):
            o, h, l, c = self.data['Open'].iloc[i], self.data['High'].iloc[i], \
                         self.data['Low'].iloc[i], self.data['Close'].iloc[i]
            body = abs(c - o)
            range_bar = h - l
            
            if range_bar == 0:
                continue
            
            upper_wick = h - max(o, c)
            lower_wick = min(o, c) - l
            
            # Bullish engulfing
            if c > self.data['Open'].iloc[i-1] and \
               self.data['Close'].iloc[i-1] < self.data['Open'].iloc[i-1] and \
               c > self.data['Open'].iloc[i-1] and o < self.data['Close'].iloc[i-1]:
                self.data.loc[self.data.index[i], 'Candle_Signal'] = 1
            
            # Bearish engulfing
            elif c < self.data['Open'].iloc[i-1] and \
                 self.data['Close'].iloc[i-1] > self.data['Open'].iloc[i-1] and \
                 c < self.data['Open'].iloc[i-1] and o > self.data['Close'].iloc[i-1]:
                self.data.loc[self.data.index[i], 'Candle_Signal'] = -1
            
            # Bullish pin bar
            elif lower_wick >= body * 2.0 and upper_wick <= body * 1.2 and \
                 c > l + range_bar * 0.60:
                self.data.loc[self.data.index[i], 'Candle_Signal'] = 1
            
            # Bearish pin bar
            elif upper_wick >= body * 2.0 and lower_wick <= body * 1.2 and \
                 c < h - range_bar * 0.60:
                self.data.loc[self.data.index[i], 'Candle_Signal'] = -1
        
        return self.data['Candle_Signal']
    
    def generate_gem_signals(self, rsi_threshold_os=28, rsi_threshold_ob=72):
        """
        Generate GEM signals: RSI + Divergence + Candlestick confirmation
        High score = all 3 signals aligned
        """
        self.data['GEM_Signal'] = 0  # 0: none, 1: bullish, -1: bearish
        self.data['Signal_Score'] = 0  # 0-3: number of confirmations
        
        for i in range(1, len(self.data)):
            rsi = self.data['RSI'].iloc[i]
            div = self.data['Divergence'].iloc[i]
            candle = self.data['Candle_Signal'].iloc[i]
            
            # Bullish signal
            if rsi < rsi_threshold_os and div == 1 and candle == 1:
                self.data.loc[self.data.index[i], 'GEM_Signal'] = 1
                self.data.loc[self.data.index[i], 'Signal_Score'] = 3
            elif rsi < rsi_threshold_os and (div == 1 or candle == 1):
                self.data.loc[self.data.index[i], 'GEM_Signal'] = 1
                self.data.loc[self.data.index[i], 'Signal_Score'] = 2
            elif rsi < rsi_threshold_os:
                self.data.loc[self.data.index[i], 'GEM_Signal'] = 1
                self.data.loc[self.data.index[i], 'Signal_Score'] = 1
            
            # Bearish signal
            elif rsi > rsi_threshold_ob and div == -1 and candle == -1:
                self.data.loc[self.data.index[i], 'GEM_Signal'] = -1
                self.data.loc[self.data.index[i], 'Signal_Score'] = 3
            elif rsi > rsi_threshold_ob and (div == -1 or candle == -1):
                self.data.loc[self.data.index[i], 'GEM_Signal'] = -1
                self.data.loc[self.data.index[i], 'Signal_Score'] = 2
            elif rsi > rsi_threshold_ob:
                self.data.loc[self.data.index[i], 'GEM_Signal'] = -1
                self.data.loc[self.data.index[i], 'Signal_Score'] = 1
        
        return self.data['GEM_Signal']
    
    def backtest(self, min_score=3, risk_ratio=4, initial_capital=10000):
        """
        Run backtest with entry on high score signals
        
        Args:
            min_score: Minimum signal score to enter (1-3)
            risk_ratio: SL to TP ratio (4 = SL is 4x TP)
            initial_capital: Starting capital
        """
        logger.info(f"Starting backtest with min_score={min_score}, risk_ratio={risk_ratio}")
        
        # Calculate indicators
        self.calculate_rsi()
        self.calculate_atr()
        self.detect_divergence()
        self.detect_candlestick_patterns()
        self.generate_gem_signals()
        
        # Backtest logic
        capital = initial_capital
        position = None  # None, 'LONG', 'SHORT'
        entry_price = 0
        entry_time = None
        tp_price = 0
        sl_price = 0
        
        for i in range(1, len(self.data)):
            current_price = self.data['Close'].iloc[i]
            current_time = self.data.index[i]
            atr = self.data['ATR'].iloc[i]
            signal = self.data['GEM_Signal'].iloc[i]
            score = self.data['Signal_Score'].iloc[i]
            
            # Skip if no ATR
            if pd.isna(atr):
                continue
            
            # Check exit conditions
            if position == 'LONG':
                if current_price >= tp_price:
                    # Take profit
                    profit = (tp_price - entry_price) * 100 / entry_price
                    capital += capital * (profit / 100)
                    self.trades.append({
                        'entry_time': entry_time,
                        'exit_time': current_time,
                        'entry_price': entry_price,
                        'exit_price': tp_price,
                        'type': 'LONG',
                        'result': 'TP',
                        'profit_pct': profit,
                        'capital': capital
                    })
                    position = None
                elif current_price <= sl_price:
                    # Stop loss
                    loss = (sl_price - entry_price) * 100 / entry_price
                    capital += capital * (loss / 100)
                    self.trades.append({
                        'entry_time': entry_time,
                        'exit_time': current_time,
                        'entry_price': entry_price,
                        'exit_price': sl_price,
                        'type': 'LONG',
                        'result': 'SL',
                        'profit_pct': loss,
                        'capital': capital
                    })
                    position = None
            
            elif position == 'SHORT':
                if current_price <= tp_price:
                    # Take profit
                    profit = (entry_price - tp_price) * 100 / entry_price
                    capital += capital * (profit / 100)
                    self.trades.append({
                        'entry_time': entry_time,
                        'exit_time': current_time,
                        'entry_price': entry_price,
                        'exit_price': tp_price,
                        'type': 'SHORT',
                        'result': 'TP',
                        'profit_pct': profit,
                        'capital': capital
                    })
                    position = None
                elif current_price >= sl_price:
                    # Stop loss
                    loss = (entry_price - sl_price) * 100 / entry_price
                    capital += capital * (loss / 100)
                    self.trades.append({
                        'entry_time': entry_time,
                        'exit_time': current_time,
                        'entry_price': entry_price,
                        'exit_price': sl_price,
                        'type': 'SHORT',
                        'result': 'SL',
                        'profit_pct': loss,
                        'capital': capital
                    })
                    position = None
            
            # Check entry conditions
            if position is None and score >= min_score:
                if signal == 1:  # Bullish
                    position = 'LONG'
                    entry_price = current_price
                    entry_time = current_time
                    tp_price = entry_price + atr  # TP = 1x ATR
                    sl_price = entry_price - (atr * risk_ratio)  # SL = 4x ATR
                
                elif signal == -1:  # Bearish
                    position = 'SHORT'
                    entry_price = current_price
                    entry_time = current_time
                    tp_price = entry_price - atr  # TP = 1x ATR
                    sl_price = entry_price + (atr * risk_ratio)  # SL = 4x ATR
            
            # Track equity
            self.equity_curve.append({
                'time': current_time,
                'capital': capital,
                'position': position
            })
        
        return self.get_performance_stats()
    
    def get_performance_stats(self):
        """Calculate and return performance statistics"""
        if not self.trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_return': 0,
                'avg_profit': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'max_drawdown': 0
            }
        
        trades_df = pd.DataFrame(self.trades)
        
        total_trades = len(trades_df)
        winning_trades = len(trades_df[trades_df['profit_pct'] > 0])
        losing_trades = len(trades_df[trades_df['profit_pct'] < 0])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        winning_sum = trades_df[trades_df['profit_pct'] > 0]['profit_pct'].sum()
        losing_sum = abs(trades_df[trades_df['profit_pct'] < 0]['profit_pct'].sum())
        
        profit_factor = winning_sum / losing_sum if losing_sum > 0 else winning_sum
        
        equity_series = pd.Series([t['capital'] for t in self.equity_curve])
        cumulative_max = equity_series.expanding().max()
        drawdown = (equity_series - cumulative_max) / cumulative_max
        max_drawdown = drawdown.min() * 100
        
        total_return = ((self.equity_curve[-1]['capital'] if self.equity_curve else 10000) - 10000) / 10000 * 100
        
        stats = {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_return': total_return,
            'avg_profit': trades_df[trades_df['profit_pct'] > 0]['profit_pct'].mean() if winning_trades > 0 else 0,
            'avg_loss': trades_df[trades_df['profit_pct'] < 0]['profit_pct'].mean() if losing_trades > 0 else 0,
            'profit_factor': profit_factor,
            'max_drawdown': max_drawdown
        }
        
        return stats
    
    def print_results(self):
        """Print detailed backtest results"""
        stats = self.get_performance_stats()
        
        print("\n" + "="*60)
        print(f"GEM SIGNALS BACKTEST RESULTS - {self.symbol}")
        print(f"Period: {self.start_date.date()} to {self.end_date.date()}")
        print("="*60)
        print(f"\nTotal Trades: {stats['total_trades']}")
        print(f"Winning Trades: {stats['winning_trades']}")
        print(f"Losing Trades: {stats['losing_trades']}")
        print(f"Win Rate: {stats['win_rate']:.2f}%")
        print(f"Profit Factor: {stats['profit_factor']:.2f}")
        print(f"Max Drawdown: {stats['max_drawdown']:.2f}%")
        print(f"Total Return: {stats['total_return']:.2f}%")
        print(f"Avg Winning Trade: {stats['avg_profit']:.2f}%")
        print(f"Avg Losing Trade: {stats['avg_loss']:.2f}%")
        print("="*60 + "\n")
        
        if self.trades:
            print("Last 10 Trades:")
            trades_df = pd.DataFrame(self.trades)
            print(trades_df.tail(10).to_string())


if __name__ == '__main__':
    # Run backtest
    backtester = GEMSignalsBacktester(
        symbol='US30',
        start_date=datetime.now() - timedelta(days=365),
        end_date=datetime.now()
    )
    
    # Fetch data
    backtester.fetch_data(interval='1h')
    
    if backtester.data is not None:
        # Run backtest with high score signals only (score >= 3)
        stats = backtester.backtest(min_score=3, risk_ratio=4)
        backtester.print_results()
