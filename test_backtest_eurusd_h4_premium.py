import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class RSIDivergenceBacktester:
    def __init__(self, symbol, timeframe, rsi_period=14, overbought=72, oversold=28):
        self.symbol = symbol
        self.timeframe = timeframe
        self.rsi_period = rsi_period
        self.overbought = overbought
        self.oversold = oversold
        self.data = None
        self.signals = None
        self.trades = []
        self.stats = {}

    def fetch_data(self):
        """Fetch historical data from yfinance with fallback"""
        try:
            # Try primary data source first
            self.data = yf.download(self.symbol, period='1y', interval=self.timeframe)
            if self.data is None or len(self.data) == 0:
                raise ValueError("No data returned from primary source")
        except Exception as e:
            print(f"Error fetching data: {e}. Using fallback yfinance...")
            self.data = yf.download(self.symbol, period='1y', interval=self.timeframe)

        if self.data is None or len(self.data) == 0:
            raise ValueError(f"Failed to fetch data for {self.symbol}")

        self.data = self.data.dropna()
        return self.data

    def calculate_rsi(self, period=None):
        """Calculate RSI"""
        if period is None:
            period = self.rsi_period

        delta = self.data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def detect_divergences(self, lookback=84):
        """Detect RSI divergences using the EDGE strategy"""
        self.data['RSI'] = self.calculate_rsi()
        self.data['In_OB'] = self.data['RSI'] > self.overbought
        self.data['In_OS'] = self.data['RSI'] < self.oversold

        self.data['Sell_Div'] = False
        self.data['Buy_Div'] = False
        self.data['Sell_Count'] = 0
        self.data['Buy_Count'] = 0

        prev_high = None
        prev_rsi_high = None
        prev_high_bar = None

        prev_low = None
        prev_rsi_low = None
        prev_low_bar = None

        for i in range(len(self.data)):
            current_price_high = self.data['High'].iloc[i]
            current_price_low = self.data['Low'].iloc[i]
            current_rsi = self.data['RSI'].iloc[i]
            current_bar = i

            # Bearish divergence
            if self.data['In_OB'].iloc[i]:
                if prev_high is None or current_rsi > prev_rsi_high:
                    prev_high = current_price_high
                    prev_rsi_high = current_rsi
                    prev_high_bar = current_bar

            if prev_high_bar is not None and current_bar - prev_high_bar > lookback:
                prev_high = None
                prev_rsi_high = None
                prev_high_bar = None

            raw_sell = (
                self.data['In_OB'].iloc[i] and
                prev_high is not None and
                current_price_high > prev_high and
                current_rsi < prev_rsi_high
            )

            if raw_sell:
                self.data.loc[self.data.index[i], 'Sell_Div'] = True

            # Bullish divergence
            if self.data['In_OS'].iloc[i]:
                if prev_low is None or current_rsi < prev_rsi_low:
                    prev_low = current_price_low
                    prev_rsi_low = current_rsi
                    prev_low_bar = current_bar

            if prev_low_bar is not None and current_bar - prev_low_bar > lookback:
                prev_low = None
                prev_rsi_low = None
                prev_low_bar = None

            raw_buy = (
                self.data['In_OS'].iloc[i] and
                prev_low is not None and
                current_price_low < prev_low and
                current_rsi > prev_rsi_low
            )

            if raw_buy:
                self.data.loc[self.data.index[i], 'Buy_Div'] = True

            # Count divergences in lookback window
            sell_count = self.data['Sell_Div'].iloc[max(0, i - lookback):i + 1].sum()
            buy_count = self.data['Buy_Div'].iloc[max(0, i - lookback):i + 1].sum()

            self.data.loc[self.data.index[i], 'Sell_Count'] = sell_count
            self.data.loc[self.data.index[i], 'Buy_Count'] = buy_count

        return self.data

    def identify_signals(self, div_count_req=3):
        """Identify strong divergence signals"""
        self.data['Buy_Signal'] = (
            self.data['Buy_Div'] & 
            (self.data['Buy_Count'] >= div_count_req)
        )
        self.data['Sell_Signal'] = (
            self.data['Sell_Div'] & 
            (self.data['Sell_Count'] >= div_count_req)
        )

        return self.data

    def backtest(self, stop_loss_pct=0.5, tp1_rr=1.0, tp2_rr=2.0):
        """Run backtest on identified signals"""
        self.trades = []
        in_trade = False
        trade_side = None  # 'BUY' or 'SELL'
        entry_price = None
        entry_idx = None
        
        for i in range(len(self.data)):
            if not in_trade:
                # Check for entry signals
                if self.data['Buy_Signal'].iloc[i]:
                    in_trade = True
                    trade_side = 'BUY'
                    entry_price = self.data['Close'].iloc[i]
                    entry_idx = i
                    
                elif self.data['Sell_Signal'].iloc[i]:
                    in_trade = True
                    trade_side = 'SELL'
                    entry_price = self.data['Close'].iloc[i]
                    entry_idx = i
            
            else:  # In trade
                current_price = self.data['Close'].iloc[i]
                
                if trade_side == 'BUY':
                    stop_price = entry_price * (1 - stop_loss_pct / 100)
                    tp1_price = entry_price + (entry_price - stop_price) * tp1_rr
                    tp2_price = entry_price + (entry_price - stop_price) * tp2_rr
                    
                    pnl = ((current_price - entry_price) / entry_price) * 100
                    
                    if current_price <= stop_price or current_price >= tp2_price:
                        self.trades.append({
                            'Side': 'BUY',
                            'Entry': entry_price,
                            'Exit': current_price,
                            'PnL%': pnl,
                            'Entry_Date': self.data.index[entry_idx],
                            'Exit_Date': self.data.index[i],
                            'Bars': i - entry_idx,
                            'TP_Hit': 'TP2' if current_price >= tp2_price else ('TP1' if current_price >= tp1_price else 'SL')
                        })
                        in_trade = False
                
                elif trade_side == 'SELL':
                    stop_price = entry_price * (1 + stop_loss_pct / 100)
                    tp1_price = entry_price - (stop_price - entry_price) * tp1_rr
                    tp2_price = entry_price - (stop_price - entry_price) * tp2_rr
                    
                    pnl = ((entry_price - current_price) / entry_price) * 100
                    
                    if current_price >= stop_price or current_price <= tp2_price:
                        self.trades.append({
                            'Side': 'SELL',
                            'Entry': entry_price,
                            'Exit': current_price,
                            'PnL%': pnl,
                            'Entry_Date': self.data.index[entry_idx],
                            'Exit_Date': self.data.index[i],
                            'Bars': i - entry_idx,
                            'TP_Hit': 'TP2' if current_price <= tp2_price else ('TP1' if current_price <= tp1_price else 'SL')
                        })
                        in_trade = False

        return pd.DataFrame(self.trades) if self.trades else pd.DataFrame()

    def calculate_stats(self, trades_df):
        """Calculate backtest statistics"""
        if trades_df.empty:
            self.stats = {'Total_Trades': 0}
            return self.stats

        total_trades = len(trades_df)
        winning_trades = len(trades_df[trades_df['PnL%'] > 0])
        losing_trades = len(trades_df[trades_df['PnL%'] <= 0])
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        avg_win = trades_df[trades_df['PnL%'] > 0]['PnL%'].mean() if winning_trades > 0 else 0
        avg_loss = trades_df[trades_df['PnL%'] <= 0]['PnL%'].mean() if losing_trades > 0 else 0
        
        total_profit = trades_df[trades_df['PnL%'] > 0]['PnL%'].sum()
        total_loss = abs(trades_df[trades_df['PnL%'] <= 0]['PnL%'].sum())
        
        profit_factor = (total_profit / total_loss) if total_loss > 0 else (99.0 if total_profit > 0 else 0.0)
        
        expectancy = (win_rate / 100 * avg_win) - ((100 - win_rate) / 100 * abs(avg_loss)) if total_trades > 0 else 0
        
        self.stats = {
            'Total_Trades': total_trades,
            'Winning_Trades': winning_trades,
            'Losing_Trades': losing_trades,
            'Win_Rate_%': round(win_rate, 2),
            'Avg_Win_%': round(avg_win, 2),
            'Avg_Loss_%': round(avg_loss, 2),
            'Profit_Factor': round(profit_factor, 2),
            'Expectancy': round(expectancy, 4),
            'Total_Profit_%': round(total_profit, 2),
            'Total_Loss_%': round(-total_loss, 2)
        }
        
        return self.stats

    def run_full_backtest(self):
        """Run complete backtest workflow"""
        print(f"\n{'='*60}")
        print(f"EURUSD H4 Premium Backtest - RSI Divergence Strategy")
        print(f"{'='*60}\n")
        
        # Fetch data
        print("[1/5] Fetching EURUSD H4 data...")
        self.fetch_data()
        print(f"     Data range: {self.data.index[0]} to {self.data.index[-1]}")
        print(f"     Total bars: {len(self.data)}")
        
        # Calculate divergences
        print("[2/5] Detecting RSI divergences...")
        self.detect_divergences()
        div_count = self.data['Buy_Div'].sum() + self.data['Sell_Div'].sum()
        print(f"     Total divergences: {div_count}")
        
        # Identify signals
        print("[3/5] Identifying strong signals (3+ divergences)...")
        self.identify_signals(div_count_req=3)
        signal_count = self.data['Buy_Signal'].sum() + self.data['Sell_Signal'].sum()
        print(f"     Total strong signals: {signal_count}")
        
        # Run backtest
        print("[4/5] Running backtest...")
        trades_df = self.backtest()
        print(f"     Total trades generated: {len(trades_df)}")
        
        # Calculate stats
        print("[5/5] Calculating statistics...")
        self.calculate_stats(trades_df)
        
        # Print results
        print(f"\n{'='*60}")
        print("BACKTEST RESULTS")
        print(f"{'='*60}")
        for key, value in self.stats.items():
            print(f"{key:.<30} {value}")
        
        if not trades_df.empty:
            print(f"\n{'='*60}")
            print("SAMPLE TRADES (First 10)")
            print(f"{'='*60}")
            print(trades_df.head(10).to_string())
        
        return trades_df, self.stats


if __name__ == "__main__":
    backtester = RSIDivergenceBacktester(
        symbol='EURUSD=X',
        timeframe='4h',
        rsi_period=14,
        overbought=72,
        oversold=28
    )
    
    trades_df, stats = backtester.run_full_backtest()
    
    # Save results
    trades_df.to_csv('data/eurusd_h4_backtest_results.csv', index=False)
    print(f"\nResults saved to: data/eurusd_h4_backtest_results.csv")
