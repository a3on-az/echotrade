import pytest
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from risk import RiskManager, PositionInfo
from signals import TradingSignal
from config import Config

class TestPositionInfo:
    
    def test_position_creation(self):
        """Test position creation and basic attributes"""
        timestamp = datetime.now()
        position = PositionInfo(
            symbol='BTC/USDT',
            side='buy',
            size=0.1,
            entry_price=50000.0,
            stop_loss=49000.0,
            timestamp=timestamp
        )
        
        assert position.symbol == 'BTC/USDT'
        assert position.side == 'buy'
        assert position.size == 0.1
        assert position.entry_price == 50000.0
        assert position.stop_loss == 49000.0
        assert position.timestamp == timestamp
        assert position.current_pnl == 0.0
    
    def test_pnl_calculation_long_position(self):
        """Test P&L calculation for long position"""
        position = PositionInfo('BTC/USDT', 'buy', 0.1, 50000.0, 49000.0, datetime.now())
        
        # Profitable trade
        pnl = position.update_pnl(52000.0)
        assert pnl == 200.0  # (52000 - 50000) * 0.1
        
        # Losing trade
        pnl = position.update_pnl(48000.0)
        assert pnl == -200.0  # (48000 - 50000) * 0.1
    
    def test_pnl_calculation_short_position(self):
        """Test P&L calculation for short position"""
        position = PositionInfo('BTC/USDT', 'sell', 0.1, 50000.0, 51000.0, datetime.now())
        
        # Profitable trade (price goes down)
        pnl = position.update_pnl(48000.0)
        assert pnl == 200.0  # (50000 - 48000) * 0.1
        
        # Losing trade (price goes up)
        pnl = position.update_pnl(52000.0)
        assert pnl == -200.0  # (50000 - 52000) * 0.1

class TestRiskManager:
    
    def setup_method(self):
        """Setup for each test"""
        self.portfolio_value = 10000.0
        self.risk_manager = RiskManager(self.portfolio_value)
    
    def test_initialization(self):
        """Test risk manager initialization"""
        rm = RiskManager(5000.0)
        assert rm.portfolio_value == 5000.0
        assert rm.peak_portfolio_value == 5000.0
        assert rm.daily_pnl == 0.0
        assert rm.max_drawdown == 0.0
        assert len(rm.open_positions) == 0
        assert rm.trades_today == 0
    
    def test_position_size_calculation(self):
        """Test position size calculation based on portfolio and signal confidence"""
        signal = TradingSignal('Test Trader', 'BTC/USDT', 'buy', 50000.0, 100.0, 0.8)
        
        position_size = self.risk_manager.calculate_position_size(signal)
        
        # Expected: portfolio * position_size_percent * confidence / price
        expected_size = (10000.0 * 0.02 * 0.8) / 50000.0
        assert abs(position_size - expected_size) < 0.000001
    
    def test_position_size_below_minimum(self):
        """Test that position size returns 0 when below minimum trade amount"""
        # Create signal with very low confidence to make position size small
        signal = TradingSignal('Test Trader', 'BTC/USDT', 'buy', 100000.0, 100.0, 0.01)
        
        position_size = self.risk_manager.calculate_position_size(signal)
        assert position_size == 0.0
    
    def test_stop_loss_calculation_long(self):
        """Test stop loss calculation for long positions"""
        stop_loss = self.risk_manager.calculate_stop_loss_price(50000.0, 'buy')
        expected = 50000.0 * 0.98  # 2% below entry
        assert abs(stop_loss - expected) < 0.01
    
    def test_stop_loss_calculation_short(self):
        """Test stop loss calculation for short positions"""
        stop_loss = self.risk_manager.calculate_stop_loss_price(50000.0, 'sell')
        expected = 50000.0 / 0.98  # 2% above entry
        assert abs(stop_loss - expected) < 1.0
    
    def test_position_limits(self):
        """Test position limits enforcement"""
        # Initially should allow positions
        assert self.risk_manager.check_position_limits() is True
        
        # Add positions up to the limit
        max_positions = Config.get_risk_params()['max_concurrent_positions']
        for i in range(max_positions):
            symbol = f'TEST{i}/USDT'
            position = PositionInfo(symbol, 'buy', 0.1, 50000.0, 49000.0, datetime.now())
            self.risk_manager.open_positions[symbol] = position
        
        # Should now reject new positions
        assert self.risk_manager.check_position_limits() is False
    
    def test_risk_caps_loss(self):
        """Test that risk management caps loss at specified drawdown limit - PRIMARY TEST"""
        # Set a lower max drawdown for testing
        with patch.object(Config, 'MAX_DRAWDOWN_PERCENT', 10.0):  # 10% max drawdown
            rm = RiskManager(10000.0)  # $10,000 portfolio
            
            # Simulate a losing position that creates 8% drawdown
            rm.portfolio_value = 9200.0  # 8% loss
            rm.peak_portfolio_value = 10000.0
            
            # Should still pass drawdown check
            assert rm.check_drawdown_limit() is True
            
            # Simulate a larger loss that creates 12% drawdown (exceeds 10% limit)
            rm.portfolio_value = 8800.0  # 12% loss
            
            # Should fail drawdown check and cap further losses
            assert rm.check_drawdown_limit() is False
    
    def test_drawdown_calculation(self):
        """Test drawdown calculation and tracking"""
        # Initial state
        current_value = self.risk_manager.calculate_current_portfolio_value()
        assert current_value == 10000.0
        assert self.risk_manager.peak_portfolio_value == 10000.0
        
        # Simulate profit - should update peak
        self.risk_manager.portfolio_value = 11000.0
        assert self.risk_manager.check_drawdown_limit() is True
        assert self.risk_manager.peak_portfolio_value == 11000.0
        
        # Simulate drawdown
        self.risk_manager.portfolio_value = 9000.0  # Down from 11000
        current_drawdown = (11000.0 - 9000.0) / 11000.0  # ~18.18%
        assert self.risk_manager.check_drawdown_limit() is True  # Still under 30% default limit
        
        # Extreme drawdown
        self.risk_manager.portfolio_value = 7000.0  # Down from 11000 = 36.36%
        assert self.risk_manager.check_drawdown_limit() is False  # Should exceed 30% limit
    
    def test_signal_validation_success(self):
        """Test successful signal validation"""
        signal = TradingSignal('Test Trader', 'BTC/USDT', 'buy', 50000.0, 100.0, 0.8)
        
        is_valid, reason = self.risk_manager.validate_signal(signal)
        assert is_valid is True
        assert reason == 'Signal validation passed'
    
    def test_signal_validation_low_confidence(self):
        """Test signal rejection due to low confidence"""
        signal = TradingSignal('Test Trader', 'BTC/USDT', 'buy', 50000.0, 100.0, 0.05)
        
        is_valid, reason = self.risk_manager.validate_signal(signal)
        assert is_valid is False
        assert 'confidence too low' in reason
    
    def test_signal_validation_invalid_symbol(self):
        """Test signal rejection for invalid trading pair"""
        signal = TradingSignal('Test Trader', 'INVALID/PAIR', 'buy', 50000.0, 100.0, 0.8)
        
        is_valid, reason = self.risk_manager.validate_signal(signal)
        assert is_valid is False
        assert 'not in allowed trading pairs' in reason
    
    def test_signal_validation_existing_position(self):
        """Test signal rejection when position already exists"""
        # Add existing position
        signal = TradingSignal('Test Trader', 'BTC/USDT', 'buy', 50000.0, 100.0, 0.8)
        position = PositionInfo('BTC/USDT', 'buy', 0.1, 50000.0, 49000.0, datetime.now())
        self.risk_manager.open_positions['BTC/USDT'] = position
        
        # Try to add same side position
        is_valid, reason = self.risk_manager.validate_signal(signal)
        assert is_valid is False
        assert 'Already have buy position' in reason
    
    def test_signal_validation_oversized_position(self):
        """Test signal rejection for oversized position"""
        # Create signal that would result in >10% portfolio allocation
        signal = TradingSignal('Test Trader', 'BTC/USDT', 'buy', 1.0, 100.0, 1.0)  # Very low price to make position huge
        
        is_valid, reason = self.risk_manager.validate_signal(signal)
        assert is_valid is False
        assert 'exceeds single trade limit' in reason
    
    def test_position_management(self):
        """Test adding and removing positions"""
        signal = TradingSignal('Test Trader', 'BTC/USDT', 'buy', 50000.0, 100.0, 0.8)
        
        # Add position
        success = self.risk_manager.add_position(signal, 50100.0, 0.004)  # Slight slippage
        assert success is True
        assert 'BTC/USDT' in self.risk_manager.open_positions
        assert self.risk_manager.trades_today == 1
        
        position = self.risk_manager.open_positions['BTC/USDT']
        assert position.entry_price == 50100.0
        assert position.size == 0.004
        
        # Remove position
        pnl = self.risk_manager.remove_position('BTC/USDT', 52000.0)  # Profitable exit
        assert pnl is not None
        assert pnl > 0  # Should be profitable
        assert 'BTC/USDT' not in self.risk_manager.open_positions
        assert self.risk_manager.portfolio_value > 10000.0  # Portfolio should increase
    
    def test_stop_loss_monitoring(self):
        """Test stop loss monitoring and triggering"""
        # Add a long position
        position = PositionInfo('BTC/USDT', 'buy', 0.1, 50000.0, 49000.0, datetime.now())
        self.risk_manager.open_positions['BTC/USDT'] = position
        
        # Market prices above stop loss - should not trigger
        market_prices = {'BTC/USDT': 50500.0}
        symbols_to_close = self.risk_manager.check_stop_losses(market_prices)
        assert len(symbols_to_close) == 0
        
        # Market prices below stop loss - should trigger
        market_prices = {'BTC/USDT': 48500.0}  # Below 49000 stop loss
        symbols_to_close = self.risk_manager.check_stop_losses(market_prices)
        assert 'BTC/USDT' in symbols_to_close
        
        # Test short position stop loss
        short_position = PositionInfo('ETH/USDT', 'sell', 1.0, 3000.0, 3060.0, datetime.now())
        self.risk_manager.open_positions['ETH/USDT'] = short_position
        
        # Price above stop loss - should trigger for short
        market_prices = {'ETH/USDT': 3100.0}
        symbols_to_close = self.risk_manager.check_stop_losses(market_prices)
        assert 'ETH/USDT' in symbols_to_close
    
    def test_risk_summary(self):
        """Test risk summary generation"""
        # Add some positions
        position1 = PositionInfo('BTC/USDT', 'buy', 0.1, 50000.0, 49000.0, datetime.now())
        position1.current_pnl = 100.0
        self.risk_manager.open_positions['BTC/USDT'] = position1
        
        self.risk_manager.daily_pnl = 50.0
        self.risk_manager.trades_today = 2
        
        summary = self.risk_manager.get_risk_summary()
        
        assert summary['portfolio_value'] == 10100.0  # Base + P&L
        assert summary['daily_pnl'] == 50.0
        assert summary['open_positions'] == 1
        assert summary['trades_today'] == 2
        assert 'position_details' in summary
        assert 'BTC/USDT' in summary['position_details']
    
    def test_daily_stats_reset(self):
        """Test that daily statistics reset properly"""
        # Set some daily stats
        self.risk_manager.trades_today = 5
        self.risk_manager.daily_pnl = 100.0
        self.risk_manager.last_reset_date = datetime.now().date() - timedelta(days=1)
        
        # Trigger reset by calling reset method
        self.risk_manager.reset_daily_stats()
        
        assert self.risk_manager.trades_today == 0
        assert self.risk_manager.daily_pnl == 0.0
        assert self.risk_manager.last_reset_date == datetime.now().date()