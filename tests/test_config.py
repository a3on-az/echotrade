import pytest
import os
from unittest.mock import patch
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import Config

class TestConfig:
    
    def test_default_values(self):
        """Test that default configuration values are set correctly"""
        assert Config.POSITION_SIZE_PERCENT == 2.0
        assert Config.STOP_LOSS_PERCENT == 2.0
        assert Config.MAX_DRAWDOWN_PERCENT == 30.0
        assert len(Config.TARGET_TRADERS) >= 2
        assert len(Config.TRADING_PAIRS) >= 2
        assert 'BTC/USDT' in Config.TRADING_PAIRS
    
    def test_risk_params(self):
        """Test risk parameter calculation"""
        risk_params = Config.get_risk_params()
        
        assert 'position_size_percent' in risk_params
        assert 'stop_loss_percent' in risk_params
        assert 'max_drawdown_percent' in risk_params
        
        assert risk_params['position_size_percent'] == 0.02  # 2%
        assert risk_params['stop_loss_percent'] == 0.02      # 2%
        assert risk_params['max_drawdown_percent'] == 0.30   # 30%
    
    @patch.dict(os.environ, {'BINANCE_API_KEY': 'test_key', 'BINANCE_API_SECRET': 'test_secret'})
    def test_config_validation_success(self):
        """Test successful configuration validation"""
        with patch.object(Config, 'API_KEY', 'test_key'):
            with patch.object(Config, 'API_SECRET', 'test_secret'):
                errors = Config.validate_config()
                assert len(errors) == 0
    
    def test_config_validation_missing_api_keys(self):
        """Test configuration validation with missing API keys"""
        with patch.object(Config, 'API_KEY', ''):
            with patch.object(Config, 'API_SECRET', ''):
                errors = Config.validate_config()
                assert len(errors) >= 2
                assert any('BINANCE_API_KEY' in error for error in errors)
                assert any('BINANCE_API_SECRET' in error for error in errors)
    
    def test_config_validation_invalid_portfolio_value(self):
        """Test configuration validation with invalid portfolio value"""
        with patch.object(Config, 'PORTFOLIO_VALUE', -1000):
            errors = Config.validate_config()
            assert any('PORTFOLIO_VALUE must be positive' in error for error in errors)
    
    def test_config_validation_invalid_position_size(self):
        """Test configuration validation with invalid position size"""
        with patch.object(Config, 'POSITION_SIZE_PERCENT', 15.0):  # Over 10%
            errors = Config.validate_config()
            assert any('POSITION_SIZE_PERCENT must be between 0 and 10' in error for error in errors)
    
    def test_target_traders_structure(self):
        """Test that target traders have required structure"""
        for trader in Config.TARGET_TRADERS:
            assert 'name' in trader
            assert 'roi_30d' in trader
            assert 'priority' in trader
            assert isinstance(trader['roi_30d'], (int, float))
            assert trader['roi_30d'] > 0