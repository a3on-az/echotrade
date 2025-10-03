import logging
import ccxt
import time
import random
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from config import Config

logger = logging.getLogger(__name__)

class TradingSignal:
    """Represents a trading signal from a copy trader"""
    
    def __init__(self, trader_name: str, symbol: str, side: str, 
                 price: float, amount: float, confidence: float = 1.0,
                 timestamp: Optional[datetime] = None):
        self.trader_name = trader_name
        self.symbol = symbol
        self.side = side  # 'buy' or 'sell'
        self.price = price
        self.amount = amount
        self.confidence = confidence  # 0.0 - 1.0
        self.timestamp = timestamp or datetime.now()
        
    def __repr__(self):
        return (f"TradingSignal({self.trader_name}, {self.symbol}, "
                f"{self.side}, {self.price}, confidence={self.confidence})")

class SignalFetcher:
    """Fetches trading signals from high-ROI traders"""
    
    def __init__(self, api_key: str, api_secret: str, sandbox: bool = True):
        # Initialize exchange for market data
        exchange_config = {
            'apiKey': api_key,
            'secret': api_secret,
            'timeout': 30000,
            'enableRateLimit': True,
        }
        
        if sandbox:
            exchange_config['sandbox'] = True
            
        self.exchange = ccxt.binance(exchange_config)
        self.target_traders = Config.TARGET_TRADERS
        self.trading_pairs = Config.TRADING_PAIRS
        self.last_signal_time = {}
        
    def fetch_market_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch current market data for a symbol"""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return {
                'symbol': symbol,
                'price': ticker['last'],
                'bid': ticker['bid'],
                'ask': ticker['ask'],
                'volume': ticker['baseVolume'],
                'change_24h': ticker['percentage']
            }
        except ccxt.BaseError as e:
            logger.error(f"Error fetching market data for {symbol}: {e}")
            return None
    
    def simulate_trader_signals(self, trader: Dict[str, Any]) -> List[TradingSignal]:
        """Simulate signals from a high-ROI trader based on market conditions"""
        signals = []
        trader_name = trader['name']
        
        # Check if enough time has passed since last signal from this trader
        min_interval = 300  # 5 minutes between signals
        if (trader_name in self.last_signal_time and 
            (datetime.now() - self.last_signal_time[trader_name]).seconds < min_interval):
            return signals
            
        try:
            for symbol in self.trading_pairs:
                market_data = self.fetch_market_data(symbol)
                if not market_data:
                    continue
                    
                # Simulate signal generation based on:
                # 1. Market volatility (higher volatility = more signals)
                # 2. Trader ROI (higher ROI = more aggressive signals)
                # 3. Recent price movements
                
                volatility_factor = abs(market_data['change_24h']) / 100
                roi_factor = trader['roi_30d'] / 1000  # Normalize ROI
                
                # Signal probability increases with volatility and trader ROI
                signal_probability = min(0.3, volatility_factor * roi_factor * 0.1)
                
                if random.random() < signal_probability:
                    # Determine signal direction based on recent price movement
                    if market_data['change_24h'] > 2:  # Strong upward movement
                        side = 'buy' if random.random() < 0.7 else 'sell'
                    elif market_data['change_24h'] < -2:  # Strong downward movement
                        side = 'sell' if random.random() < 0.7 else 'buy'
                    else:
                        side = random.choice(['buy', 'sell'])
                    
                    # Calculate signal strength based on trader priority and market conditions
                    confidence = min(1.0, (roi_factor + volatility_factor) / 2)
                    
                    # Position size based on trader ROI and confidence
                    base_amount = 100 * (trader['roi_30d'] / 1000)  # Scale with ROI
                    amount = base_amount * confidence
                    
                    signal = TradingSignal(
                        trader_name=trader_name,
                        symbol=symbol,
                        side=side,
                        price=market_data['ask'] if side == 'buy' else market_data['bid'],
                        amount=amount,
                        confidence=confidence
                    )
                    
                    signals.append(signal)
                    logger.info(f"Generated signal: {signal}")
                    
        except Exception as e:
            logger.error(f"Error simulating signals for {trader_name}: {e}")
            
        if signals:
            self.last_signal_time[trader_name] = datetime.now()
            
        return signals
    
    def fetch_signals(self) -> List[TradingSignal]:
        """Fetch all trading signals from target traders"""
        all_signals = []
        
        try:
            # Sort traders by priority and ROI
            sorted_traders = sorted(self.target_traders, 
                                  key=lambda x: (x['priority'], -x['roi_30d']))
            
            for trader in sorted_traders:
                trader_signals = self.simulate_trader_signals(trader)
                all_signals.extend(trader_signals)
                
                # Add small delay between trader signal fetching
                time.sleep(0.1)
                
            logger.info(f"Fetched {len(all_signals)} signals from {len(sorted_traders)} traders")
            return all_signals
            
        except Exception as e:
            logger.error(f"Error fetching signals: {e}")
            return []
    
    def get_signal_strength(self, signals: List[TradingSignal], symbol: str) -> Dict[str, float]:
        """Analyze signal strength for a specific symbol"""
        symbol_signals = [s for s in signals if s.symbol == symbol]
        
        if not symbol_signals:
            return {'buy_strength': 0.0, 'sell_strength': 0.0, 'net_sentiment': 0.0}
        
        buy_signals = [s for s in symbol_signals if s.side == 'buy']
        sell_signals = [s for s in symbol_signals if s.side == 'sell']
        
        buy_strength = sum(s.confidence for s in buy_signals) / len(symbol_signals)
        sell_strength = sum(s.confidence for s in sell_signals) / len(symbol_signals)
        
        net_sentiment = buy_strength - sell_strength
        
        return {
            'buy_strength': buy_strength,
            'sell_strength': sell_strength,
            'net_sentiment': net_sentiment,
            'total_signals': len(symbol_signals)
        }
