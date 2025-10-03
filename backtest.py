#!/usr/bin/env python3
"""
EchoTradeBot - Advanced Backtesting Engine
Simulates historical trading performance with realistic slippage and fees
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import ccxt
from typing import Dict, List, Tuple, Optional
import logging
from dataclasses import dataclass

# Import Phase 1 components
from config import Config
from signals import TradingSignal, SignalFetcher
from risk import RiskManager
from execution import OrderExecutor

logger = logging.getLogger(__name__)

@dataclass
class BacktestResult:
    """Results from a backtest run"""
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    total_return: float
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    total_trades: int
    profit_factor: float
    equity_curve: pd.Series
    trades: List[Dict]
    metrics: Dict

class BacktestEngine:
    """Professional backtesting engine with realistic market simulation"""
    
    def __init__(self, initial_capital: float = 10000, slippage: float = 0.001):
        self.initial_capital = initial_capital
        self.slippage = slippage  # 0.1% slippage
        self.commission = 0.001  # 0.1% commission
        
        # Initialize components
        self.risk_manager = RiskManager(initial_capital)
        self.signal_fetcher = SignalFetcher(
            api_key=Config.API_KEY,
            api_secret=Config.API_SECRET,
            sandbox=True
        )
        
    def get_historical_data(self, symbol: str, start_date: datetime, 
                          end_date: datetime, timeframe: str = '1h') -> pd.DataFrame:
        """Fetch historical OHLCV data"""
        try:
            # Use CCXT to fetch historical data
            exchange = ccxt.binance({
                'apiKey': Config.API_KEY,
                'secret': Config.API_SECRET,
                'sandbox': False,  # Use production for historical data
                'enableRateLimit': True,
            })
            
            # Convert dates to milliseconds
            start_ms = int(start_date.timestamp() * 1000)
            end_ms = int(end_date.timestamp() * 1000)
            
            # Fetch OHLCV data
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, start_ms, limit=1000)
            
            # Convert to DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            logger.warning(f"Could not fetch real data for {symbol}: {e}")
            # Generate synthetic data for backtesting
            return self._generate_synthetic_data(symbol, start_date, end_date, timeframe)
    
    def _generate_synthetic_data(self, symbol: str, start_date: datetime, 
                                end_date: datetime, timeframe: str = '1h') -> pd.DataFrame:
        """Generate realistic synthetic price data for backtesting"""
        
        # Base prices for different symbols
        base_prices = {
            'BTC/USDT': 45000,
            'ETH/USDT': 2800,
            'BNB/USDT': 300,
            'ADA/USDT': 0.45
        }
        
        base_price = base_prices.get(symbol, 100)
        
        # Generate time series
        freq = '1H' if timeframe == '1h' else '1D'
        dates = pd.date_range(start=start_date, end=end_date, freq=freq)
        
        # Generate realistic price movements
        n_periods = len(dates)
        returns = np.random.normal(0.0002, 0.02, n_periods)  # Small positive drift, 2% volatility
        
        # Create price series with geometric brownian motion
        prices = [base_price]
        for i in range(1, n_periods):
            price = prices[-1] * (1 + returns[i])
            prices.append(price)
        
        # Generate OHLCV data
        df = pd.DataFrame(index=dates)
        df['close'] = prices
        df['open'] = df['close'].shift(1).fillna(df['close'].iloc[0])
        
        # Generate high and low with realistic spreads
        spread = df['close'] * 0.01  # 1% spread
        df['high'] = df[['open', 'close']].max(axis=1) + spread * np.random.uniform(0, 1, n_periods)
        df['low'] = df[['open', 'close']].min(axis=1) - spread * np.random.uniform(0, 1, n_periods)
        
        # Generate volume
        df['volume'] = np.random.uniform(1000, 10000, n_periods)
        
        return df
    
    def simulate_trader_signals(self, price_data: Dict[str, pd.DataFrame], 
                               trader_name: str = "Yun Qiang") -> List[TradingSignal]:
        """Simulate trading signals based on price movements"""
        signals = []
        
        for symbol, df in price_data.items():
            # Simple momentum strategy for simulation
            df['returns'] = df['close'].pct_change()
            df['sma_20'] = df['close'].rolling(20).mean()
            df['sma_50'] = df['close'].rolling(50).mean()
            
            for i in range(50, len(df)):  # Start after SMA calculation
                current_price = df['close'].iloc[i]
                sma_20 = df['sma_20'].iloc[i]
                sma_50 = df['sma_50'].iloc[i]
                timestamp = df.index[i]
                
                # Generate signals based on SMA crossover with some noise
                if sma_20 > sma_50 and np.random.random() < 0.15:  # 15% chance of buy signal
                    confidence = min(0.9, 0.5 + (sma_20 - sma_50) / sma_50)
                    
                    signal = TradingSignal(
                        trader_name=trader_name,
                        symbol=symbol,
                        side='buy',
                        price=current_price,
                        amount=0.1,  # Will be adjusted by risk management
                        confidence=confidence,
                        timestamp=timestamp
                    )
                    signals.append(signal)
                
                elif sma_20 < sma_50 and np.random.random() < 0.1:  # 10% chance of sell signal
                    confidence = min(0.9, 0.5 + (sma_50 - sma_20) / sma_50)
                    
                    signal = TradingSignal(
                        trader_name=trader_name,
                        symbol=symbol,
                        side='sell',
                        price=current_price,
                        amount=0.1,
                        confidence=confidence,
                        timestamp=timestamp
                    )
                    signals.append(signal)
        
        return sorted(signals, key=lambda x: x.timestamp)
    
    def calculate_slippage_price(self, price: float, side: str) -> float:
        """Calculate realistic slippage"""
        if side == 'buy':
            return price * (1 + self.slippage)
        else:
            return price * (1 - self.slippage)
    
    def run_backtest(self, start_date: datetime, end_date: datetime, 
                    traders: List[str] = None) -> BacktestResult:
        """Run comprehensive backtest simulation"""
        
        logger.info(f"🔄 Starting backtest from {start_date} to {end_date}")
        
        if traders is None:
            traders = ["Yun Qiang", "Crypto Loby"]
        
        # Reset risk manager
        self.risk_manager = RiskManager(self.initial_capital)
        
        # Fetch historical data for all trading pairs
        price_data = {}
        for symbol in Config.TRADING_PAIRS:
            logger.info(f"📊 Fetching data for {symbol}")
            price_data[symbol] = self.get_historical_data(symbol, start_date, end_date)
        
        # Generate signals from all traders
        all_signals = []
        for trader in traders:
            trader_signals = self.simulate_trader_signals(price_data, trader)
            all_signals.extend(trader_signals)
        
        # Sort signals by timestamp
        all_signals.sort(key=lambda x: x.timestamp)
        
        # Simulation variables
        current_capital = self.initial_capital
        peak_capital = self.initial_capital
        max_drawdown = 0.0
        equity_curve = []
        executed_trades = []
        
        daily_returns = []
        
        logger.info(f"🎯 Processing {len(all_signals)} signals")
        
        # Process each signal
        for i, signal in enumerate(all_signals):
            # Update risk manager portfolio value
            self.risk_manager.portfolio_value = current_capital
            
            # Validate signal
            is_valid, reason = self.risk_manager.validate_signal(signal)
            
            if not is_valid:
                continue
            
            # Calculate position size
            position_size = self.risk_manager.calculate_position_size(signal)
            if position_size <= 0:
                continue
            
            # Apply slippage
            fill_price = self.calculate_slippage_price(signal.price, signal.side)
            
            # Calculate trade value
            trade_value = position_size * fill_price
            commission_cost = trade_value * self.commission
            
            # Check if we have enough capital
            if trade_value + commission_cost > current_capital * 0.95:  # 95% max utilization
                continue
            
            # Execute trade
            self.risk_manager.add_position(signal, fill_price, position_size)
            
            # Simulate holding period (random 1-24 hours)
            holding_hours = np.random.randint(1, 25)
            exit_timestamp = signal.timestamp + timedelta(hours=holding_hours)
            
            # Find exit price
            symbol_data = price_data[signal.symbol]
            exit_price_candidates = symbol_data[symbol_data.index >= exit_timestamp]
            
            if len(exit_price_candidates) == 0:
                continue
            
            exit_price = exit_price_candidates.iloc[0]['close']
            
            # Apply slippage for exit
            exit_fill_price = self.calculate_slippage_price(exit_price, 
                                                          'sell' if signal.side == 'buy' else 'buy')
            
            # Calculate P&L
            if signal.side == 'buy':
                pnl = (exit_fill_price - fill_price) * position_size
            else:
                pnl = (fill_price - exit_fill_price) * position_size
            
            # Subtract commission for exit
            exit_commission = exit_fill_price * position_size * self.commission
            net_pnl = pnl - commission_cost - exit_commission
            
            # Update capital
            current_capital += net_pnl
            
            # Track peak and drawdown
            if current_capital > peak_capital:
                peak_capital = current_capital
            
            current_drawdown = (peak_capital - current_capital) / peak_capital
            if current_drawdown > max_drawdown:
                max_drawdown = current_drawdown
            
            # Record trade
            trade_record = {
                'timestamp': signal.timestamp,
                'exit_timestamp': exit_timestamp,
                'symbol': signal.symbol,
                'side': signal.side,
                'entry_price': fill_price,
                'exit_price': exit_fill_price,
                'size': position_size,
                'pnl': net_pnl,
                'trader': signal.trader_name
            }
            executed_trades.append(trade_record)
            
            # Record equity point
            equity_curve.append({
                'timestamp': exit_timestamp,
                'equity': current_capital,
                'drawdown': current_drawdown
            })
            
            # Calculate daily return
            if i > 0:
                daily_return = net_pnl / current_capital
                daily_returns.append(daily_return)
            
            # Remove position from risk manager
            self.risk_manager.remove_position(signal.symbol, exit_fill_price)
        
        # Calculate final metrics
        total_return = (current_capital - self.initial_capital) / self.initial_capital
        
        # Annualized return
        days = (end_date - start_date).days
        annual_return = (1 + total_return) ** (365 / days) - 1 if days > 0 else 0
        
        # Sharpe ratio
        if len(daily_returns) > 1:
            sharpe_ratio = np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(365) if np.std(daily_returns) > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Win rate
        winning_trades = [t for t in executed_trades if t['pnl'] > 0]
        win_rate = len(winning_trades) / len(executed_trades) * 100 if executed_trades else 0
        
        # Profit factor
        gross_profit = sum(t['pnl'] for t in executed_trades if t['pnl'] > 0)
        gross_loss = abs(sum(t['pnl'] for t in executed_trades if t['pnl'] < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Create equity curve series
        equity_df = pd.DataFrame(equity_curve)
        if not equity_df.empty:
            equity_series = equity_df.set_index('timestamp')['equity']
        else:
            equity_series = pd.Series([self.initial_capital], index=[start_date])
        
        logger.info(f"✅ Backtest completed: {len(executed_trades)} trades, {total_return:.2%} return")
        
        return BacktestResult(
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.initial_capital,
            final_capital=current_capital,
            total_return=total_return * 100,  # Convert to percentage
            annual_return=annual_return * 100,
            max_drawdown=max_drawdown * 100,
            sharpe_ratio=sharpe_ratio,
            win_rate=win_rate,
            total_trades=len(executed_trades),
            profit_factor=profit_factor,
            equity_curve=equity_series,
            trades=executed_trades,
            metrics={
                'gross_profit': gross_profit,
                'gross_loss': gross_loss,
                'avg_win': np.mean([t['pnl'] for t in executed_trades if t['pnl'] > 0]) if winning_trades else 0,
                'avg_loss': np.mean([t['pnl'] for t in executed_trades if t['pnl'] < 0]) if len(executed_trades) > len(winning_trades) else 0,
                'largest_win': max([t['pnl'] for t in executed_trades]) if executed_trades else 0,
                'largest_loss': min([t['pnl'] for t in executed_trades]) if executed_trades else 0,
            }
        )
    
    def optimize_parameters(self, start_date: datetime, end_date: datetime, 
                          param_ranges: Dict) -> Dict:
        """Optimize trading parameters using grid search"""
        
        best_return = float('-inf')
        best_params = {}
        
        # Example parameter optimization
        position_sizes = param_ranges.get('position_size', [1.0, 2.0, 3.0])
        stop_losses = param_ranges.get('stop_loss', [1.0, 2.0, 3.0])
        
        logger.info(f"🔧 Optimizing parameters over {len(position_sizes) * len(stop_losses)} combinations")
        
        for pos_size in position_sizes:
            for stop_loss in stop_losses:
                # Update config temporarily
                original_pos_size = Config.POSITION_SIZE_PERCENT
                original_stop_loss = Config.STOP_LOSS_PERCENT
                
                Config.POSITION_SIZE_PERCENT = pos_size
                Config.STOP_LOSS_PERCENT = stop_loss
                
                try:
                    # Run backtest
                    result = self.run_backtest(start_date, end_date)
                    
                    # Check if this is the best result
                    risk_adjusted_return = result.total_return / max(abs(result.max_drawdown), 1)
                    
                    if risk_adjusted_return > best_return:
                        best_return = risk_adjusted_return
                        best_params = {
                            'position_size': pos_size,
                            'stop_loss': stop_loss,
                            'return': result.total_return,
                            'max_drawdown': result.max_drawdown,
                            'sharpe_ratio': result.sharpe_ratio
                        }
                
                except Exception as e:
                    logger.error(f"Optimization failed for params {pos_size}, {stop_loss}: {e}")
                
                finally:
                    # Restore original config
                    Config.POSITION_SIZE_PERCENT = original_pos_size
                    Config.STOP_LOSS_PERCENT = original_stop_loss
        
        logger.info(f"🎯 Best parameters found: {best_params}")
        return best_params

# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Initialize backtest engine
    engine = BacktestEngine(initial_capital=10000, slippage=0.001)
    
    # Run backtest
    start_date = datetime.now() - timedelta(days=30)
    end_date = datetime.now()
    
    print("🚀 Running EchoTrade Backtest...")
    result = engine.run_backtest(start_date, end_date)
    
    print(f"\n📊 BACKTEST RESULTS")
    print(f"{'='*50}")
    print(f"Period: {result.start_date.date()} to {result.end_date.date()}")
    print(f"Initial Capital: ${result.initial_capital:,.2f}")
    print(f"Final Capital: ${result.final_capital:,.2f}")
    print(f"Total Return: {result.total_return:+.2f}%")
    print(f"Max Drawdown: {result.max_drawdown:.2f}%")
    print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
    print(f"Win Rate: {result.win_rate:.1f}%")
    print(f"Total Trades: {result.total_trades}")
    print(f"Profit Factor: {result.profit_factor:.2f}")
    
    if result.trades:
        print(f"\n🏆 TRADE SUMMARY")
        print(f"Average Win: ${result.metrics['avg_win']:+.2f}")
        print(f"Average Loss: ${result.metrics['avg_loss']:+.2f}")
        print(f"Largest Win: ${result.metrics['largest_win']:+.2f}")
        print(f"Largest Loss: ${result.metrics['largest_loss']:+.2f}")
    
    print(f"\n✅ Backtest completed successfully!")