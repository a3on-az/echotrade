#!/usr/bin/env python3
"""
WebSocket Live Price Feed
Real-time price streaming from Binance
"""

import asyncio
import ccxt.async_support as ccxt_async
import logging
from datetime import datetime
from typing import Dict, List, Callable, Optional
from collections import deque
import json

logger = logging.getLogger(__name__)

class PriceFeed:
    """Real-time price feed using Binance WebSocket"""

    def __init__(self, symbols: List[str], api_key: str = None, api_secret: str = None):
        self.symbols = symbols
        self.exchange = ccxt_async.binance({
            'apiKey': api_key or '',
            'secret': api_secret or '',
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })

        # Price data storage
        self.current_prices = {}
        self.price_history = {symbol: deque(maxlen=1000) for symbol in symbols}
        self.subscribers = []
        self.running = False

    async def start(self):
        """Start the price feed"""
        self.running = True
        logger.info(f"Starting price feed for {len(self.symbols)} symbols")

        try:
            # Start WebSocket streams
            tasks = [self._stream_symbol(symbol) for symbol in self.symbols]
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            logger.error(f"Price feed error: {e}")
        finally:
            await self.close()

    async def _stream_symbol(self, symbol: str):
        """Stream prices for a single symbol"""
        while self.running:
            try:
                # Fetch ticker data
                ticker = await self.exchange.fetch_ticker(symbol)

                price_update = {
                    'symbol': symbol,
                    'price': ticker['last'],
                    'bid': ticker['bid'],
                    'ask': ticker['ask'],
                    'volume': ticker['baseVolume'],
                    'change_24h': ticker['percentage'],
                    'high_24h': ticker['high'],
                    'low_24h': ticker['low'],
                    'timestamp': ticker['timestamp'] or int(datetime.now().timestamp() * 1000)
                }

                # Store current price
                self.current_prices[symbol] = price_update

                # Add to history
                self.price_history[symbol].append({
                    'timestamp': price_update['timestamp'],
                    'price': price_update['price']
                })

                # Notify subscribers
                await self._notify_subscribers(price_update)

                # Wait before next fetch (rate limiting)
                await asyncio.sleep(1)  # 1 second between updates

            except Exception as e:
                logger.error(f"Error streaming {symbol}: {e}")
                await asyncio.sleep(5)  # Wait longer on error

    async def _notify_subscribers(self, price_update: Dict):
        """Notify all subscribers of price update"""
        for callback in self.subscribers:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(price_update)
                else:
                    callback(price_update)
            except Exception as e:
                logger.error(f"Subscriber notification error: {e}")

    def subscribe(self, callback: Callable):
        """Subscribe to price updates"""
        self.subscribers.append(callback)
        logger.info(f"Added subscriber: {callback.__name__}")

    def unsubscribe(self, callback: Callable):
        """Unsubscribe from price updates"""
        if callback in self.subscribers:
            self.subscribers.remove(callback)
            logger.info(f"Removed subscriber: {callback.__name__}")

    def get_current_price(self, symbol: str) -> Optional[Dict]:
        """Get current price for symbol"""
        return self.current_prices.get(symbol)

    def get_price_history(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Get price history for symbol"""
        history = self.price_history.get(symbol, deque())
        return list(history)[-limit:]

    def stop(self):
        """Stop the price feed"""
        self.running = False
        logger.info("Stopping price feed")

    async def close(self):
        """Close exchange connection"""
        await self.exchange.close()


class CandlestickFeed:
    """OHLCV candlestick data provider"""

    def __init__(self, symbols: List[str], api_key: str = None, api_secret: str = None):
        self.symbols = symbols
        self.exchange = ccxt_async.binance({
            'apiKey': api_key or '',
            'secret': api_secret or '',
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })

        # Candlestick storage
        self.candles = {}
        self.running = False

    async def fetch_ohlcv(self, symbol: str, timeframe: str = '1m', limit: int = 100) -> List[Dict]:
        """
        Fetch OHLCV candlestick data

        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            timeframe: Candlestick timeframe ('1m', '5m', '15m', '1h', '4h', '1d')
            limit: Number of candles to fetch

        Returns:
            List of candlestick dictionaries with OHLCV data
        """
        try:
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)

            # Format candlesticks
            candles = []
            for candle in ohlcv:
                candles.append({
                    'timestamp': candle[0],
                    'datetime': datetime.fromtimestamp(candle[0] / 1000).isoformat(),
                    'open': candle[1],
                    'high': candle[2],
                    'low': candle[3],
                    'close': candle[4],
                    'volume': candle[5]
                })

            # Cache the candles
            cache_key = f"{symbol}_{timeframe}"
            self.candles[cache_key] = candles

            return candles

        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol} {timeframe}: {e}")
            return []

    async def get_latest_candle(self, symbol: str, timeframe: str = '1m') -> Optional[Dict]:
        """Get the most recent candlestick"""
        candles = await self.fetch_ohlcv(symbol, timeframe, limit=1)
        return candles[0] if candles else None

    def get_cached_candles(self, symbol: str, timeframe: str = '1m') -> List[Dict]:
        """Get cached candlesticks (no API call)"""
        cache_key = f"{symbol}_{timeframe}"
        return self.candles.get(cache_key, [])

    async def close(self):
        """Close exchange connection"""
        await self.exchange.close()


# Singleton instances
_price_feed = None
_candlestick_feed = None

def get_price_feed(symbols: List[str], api_key: str = None, api_secret: str = None) -> PriceFeed:
    """Get or create price feed singleton"""
    global _price_feed
    if _price_feed is None:
        _price_feed = PriceFeed(symbols, api_key, api_secret)
    return _price_feed

def get_candlestick_feed(symbols: List[str], api_key: str = None, api_secret: str = None) -> CandlestickFeed:
    """Get or create candlestick feed singleton"""
    global _candlestick_feed
    if _candlestick_feed is None:
        _candlestick_feed = CandlestickFeed(symbols, api_key, api_secret)
    return _candlestick_feed


# Example usage
if __name__ == "__main__":
    async def main():
        # Test price feed
        feed = PriceFeed(['BTC/USDT', 'ETH/USDT'])

        def print_price(update):
            print(f"{update['symbol']}: ${update['price']:,.2f} ({update['change_24h']:+.2f}%)")

        feed.subscribe(print_price)

        # Run for 30 seconds
        task = asyncio.create_task(feed.start())
        await asyncio.sleep(30)
        feed.stop()
        await task

    asyncio.run(main())
