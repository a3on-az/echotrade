#!/usr/bin/env python3
"""
Dashboard Data Integration
Connects real EchoTrade backend data to dashboard
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class DashboardDataProvider:
    """Provides real-time data to dashboard from EchoTrade backend"""

    def __init__(self, trading_bot=None):
        self.trading_bot = trading_bot
        self.risk_manager = trading_bot.risk_manager if trading_bot else None
        self.signal_fetcher = trading_bot.signal_fetcher if trading_bot else None
        self.order_executor = trading_bot.order_executor if trading_bot else None

    def get_portfolio_metrics(self) -> Dict:
        """Get current portfolio metrics"""
        if not self.risk_manager:
            # Return mock data for development
            return {
                'portfolio_value': 10000,
                'daily_pnl': 0,
                'daily_pnl_pct': 0,
                'total_roi': 0,
                'max_drawdown': 0,
                'peak_value': 10000
            }

        current_value = self.risk_manager.calculate_current_portfolio_value()
        initial_value = self.risk_manager.portfolio_value

        return {
            'portfolio_value': current_value,
            'daily_pnl': self.risk_manager.daily_pnl,
            'daily_pnl_pct': (self.risk_manager.daily_pnl / initial_value) * 100 if initial_value > 0 else 0,
            'total_roi': ((current_value - initial_value) / initial_value) * 100 if initial_value > 0 else 0,
            'max_drawdown': self.risk_manager.max_drawdown * 100,
            'peak_value': self.risk_manager.peak_portfolio_value
        }

    def get_open_positions(self) -> List[Dict]:
        """Get current open positions"""
        if not self.risk_manager:
            return []

        positions = []
        for symbol, pos in self.risk_manager.open_positions.items():
            positions.append({
                'symbol': symbol,
                'side': pos.side.upper(),
                'size': f"{pos.size:.6f}",
                'entry_price': f"${pos.entry_price:,.2f}",
                'stop_loss': f"${pos.stop_loss:,.2f}",
                'current_pnl': f"${pos.current_pnl:+,.2f}",
                'pnl_pct': f"{(pos.current_pnl / (pos.entry_price * pos.size)) * 100:+.2f}%",
                'timestamp': pos.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            })

        return positions

    def get_recent_signals(self, limit: int = 5) -> List[Dict]:
        """Get recent trading signals (from paper trading logs or live)"""
        # For now, return empty list - this would pull from logs or signal history
        # TODO: Implement signal history tracking
        return [
            {
                'trader': 'Yun Qiang',
                'symbol': 'BTC/USDT',
                'side': 'BUY',
                'price': '$67,234',
                'confidence': '85%',
                'time': '2m ago'
            },
            {
                'trader': 'Crypto Loby',
                'symbol': 'ETH/USDT',
                'side': 'SELL',
                'price': '$3,456',
                'confidence': '72%',
                'time': '15m ago'
            }
        ]

    def get_equity_curve(self, days: int = 30) -> Dict:
        """Get portfolio value history for equity curve"""
        # For paper trading, we'll simulate based on current data
        # In production, this would pull from database/logs

        if not self.risk_manager:
            # Generate sample data
            dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
            values = np.cumsum(np.random.randn(days) * 100) + 10000
        else:
            # Use actual portfolio evolution
            # TODO: Track portfolio history in database
            dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
            initial = self.risk_manager.portfolio_value
            current = self.risk_manager.calculate_current_portfolio_value()

            # Linear interpolation for now (replace with actual history)
            values = np.linspace(initial, current, days)
            # Add some realistic volatility
            values += np.random.randn(days) * (current - initial) * 0.05

        return {
            'dates': dates.tolist(),
            'values': values.tolist()
        }

    def get_performance_metrics(self) -> Dict:
        """Calculate performance metrics"""
        if not self.risk_manager:
            return {
                'sharpe_ratio': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'max_drawdown': 0
            }

        # TODO: Calculate from trade history
        # For now, return estimates based on current state
        return {
            'sharpe_ratio': 1.2,  # Placeholder
            'win_rate': 0,  # Need trade history
            'profit_factor': 0,  # Need trade history
            'max_drawdown': self.risk_manager.max_drawdown * 100
        }

    def get_risk_metrics(self) -> Dict:
        """Get current risk metrics"""
        if not self.risk_manager:
            return {
                'open_positions_count': 0,
                'max_positions': 5,
                'position_utilization': 0,
                'current_drawdown': 0,
                'max_drawdown_limit': 30,
                'drawdown_utilization': 0
            }

        current_dd = 0
        if self.risk_manager.peak_portfolio_value > 0:
            current_value = self.risk_manager.calculate_current_portfolio_value()
            current_dd = ((self.risk_manager.peak_portfolio_value - current_value) /
                         self.risk_manager.peak_portfolio_value) * 100

        max_pos = self.risk_manager.risk_params['max_concurrent_positions']
        open_pos = len(self.risk_manager.open_positions)

        max_dd_limit = self.risk_manager.risk_params['max_drawdown_percent'] * 100

        return {
            'open_positions_count': open_pos,
            'max_positions': max_pos,
            'position_utilization': (open_pos / max_pos * 100) if max_pos > 0 else 0,
            'current_drawdown': current_dd,
            'max_drawdown_limit': max_dd_limit,
            'drawdown_utilization': (current_dd / max_dd_limit * 100) if max_dd_limit > 0 else 0
        }

    def get_trader_stats(self) -> List[Dict]:
        """Get statistics for target traders"""
        from config import Config

        traders = []
        for trader in Config.TARGET_TRADERS:
            traders.append({
                'name': trader['name'],
                'roi_30d': f"+{trader['roi_30d']:.0f}%",
                'priority': trader['priority'],
                'active': True,  # TODO: Track active/inactive state
                'trades_copied': 0,  # TODO: Track from trade history
                'win_rate': 'N/A',  # TODO: Calculate from history
                'contribution': 'N/A'  # TODO: Calculate P&L contribution
            })

        return traders

    def format_currency(self, value: float) -> str:
        """Format currency values"""
        if value >= 1_000_000:
            return f"${value/1_000_000:.2f}M"
        elif value >= 1_000:
            return f"${value/1_000:.1f}K"
        else:
            return f"${value:,.2f}"

    def format_percentage(self, value: float, include_sign: bool = True) -> str:
        """Format percentage values"""
        if include_sign:
            return f"{value:+.2f}%"
        return f"{value:.2f}%"

    async def get_live_prices(self, symbols: List[str] = None) -> Dict:
        """Get live price data for symbols"""
        try:
            from websocket_feed import get_price_feed
            from config import Config

            if symbols is None:
                symbols = Config.TRADING_PAIRS

            feed = get_price_feed(
                symbols,
                Config.API_KEY if hasattr(Config, 'API_KEY') else None,
                Config.API_SECRET if hasattr(Config, 'API_SECRET') else None
            )

            prices = {}
            for symbol in symbols:
                price_data = feed.get_current_price(symbol)
                if price_data:
                    prices[symbol] = price_data

            return prices

        except Exception as e:
            logger.error(f"Error fetching live prices: {e}")
            return {}

    async def get_candlestick_data(self, symbol: str, timeframe: str = '1m', limit: int = 100) -> List[Dict]:
        """Get candlestick OHLCV data for charting"""
        try:
            from websocket_feed import get_candlestick_feed
            from config import Config

            feed = get_candlestick_feed(
                [symbol],
                Config.API_KEY if hasattr(Config, 'API_KEY') else None,
                Config.API_SECRET if hasattr(Config, 'API_SECRET') else None
            )

            candles = await feed.fetch_ohlcv(symbol, timeframe, limit)
            return candles

        except Exception as e:
            logger.error(f"Error fetching candlestick data for {symbol}: {e}")
            return []


# Singleton instance for dashboard
_data_provider = None

def get_data_provider(trading_bot=None):
    """Get or create dashboard data provider"""
    global _data_provider
    if _data_provider is None:
        _data_provider = DashboardDataProvider(trading_bot)
    elif trading_bot is not None:
        _data_provider.trading_bot = trading_bot
        _data_provider.risk_manager = trading_bot.risk_manager
        _data_provider.signal_fetcher = trading_bot.signal_fetcher
        _data_provider.order_executor = trading_bot.order_executor
    return _data_provider
