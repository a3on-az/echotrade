import pytest
import os
import sys
from unittest.mock import patch, MagicMock
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from execution import OrderExecutor, OrderResult
from signals import TradingSignal
import ccxt

class TestOrderResult:
    
    def test_order_result_creation(self):
        """Test order result creation"""
        result = OrderResult(
            success=True,
            order_id='test_order_123',
            fill_price=50000.0,
            fill_amount=0.1
        )
        
        assert result.success is True
        assert result.order_id == 'test_order_123'
        assert result.fill_price == 50000.0
        assert result.fill_amount == 0.1
        assert result.error is None
        assert isinstance(result.timestamp, (int, float))
    
    def test_order_result_error(self):
        """Test order result with error"""
        result = OrderResult(
            success=False,
            error='Insufficient funds'
        )
        
        assert result.success is False
        assert result.error == 'Insufficient funds'
        assert result.order_id is None
        assert result.fill_price is None

class TestOrderExecutor:
    
    def setup_method(self):
        """Setup for each test"""
        self.api_key = 'test_api_key'
        self.api_secret = 'test_api_secret'
    
    def test_paper_trading_initialization(self):
        """Test initialization in paper trading mode"""
        executor = OrderExecutor(self.api_key, self.api_secret, paper_trading=True)
        
        assert executor.paper_trading is True
        assert executor.exchange is None
        assert executor.retry_attempts == 3
        assert executor.retry_delay == 1.0
    
    @patch('execution.ccxt.binance')
    def test_real_trading_initialization(self, mock_binance):
        """Test initialization in real trading mode"""
        mock_exchange = MagicMock()
        mock_binance.return_value = mock_exchange
        
        executor = OrderExecutor(self.api_key, self.api_secret, paper_trading=False, sandbox=True)
        
        assert executor.paper_trading is False
        assert executor.exchange == mock_exchange
        mock_binance.assert_called_once()
    
    def test_paper_trading_order_simulation(self):
        """Test paper trading order simulation"""
        executor = OrderExecutor(self.api_key, self.api_secret, paper_trading=True)
        signal = TradingSignal('Test Trader', 'BTC/USDT', 'buy', 50000.0, 100.0, 0.8)
        
        result = executor.execute_signal_order(signal, 0.1)
        
        assert result.success is True
        assert result.order_id is not None
        assert 'PAPER_' in result.order_id
        assert result.fill_price is not None
        assert result.fill_amount is not None
        assert abs(result.fill_price - 50000.0) < 1000  # Should be close to signal price
        assert abs(result.fill_amount - 0.1) < 0.01  # Should be close to requested amount
    
    def test_paper_trading_slippage_simulation(self):
        """Test that paper trading simulates realistic slippage"""
        executor = OrderExecutor(self.api_key, self.api_secret, paper_trading=True)
        
        # Buy order should have positive slippage (higher price)
        buy_signal = TradingSignal('Test Trader', 'BTC/USDT', 'buy', 50000.0, 100.0, 0.8)
        buy_result = executor.execute_signal_order(buy_signal, 0.1)
        
        # Sell order should have negative slippage (lower price)
        sell_signal = TradingSignal('Test Trader', 'BTC/USDT', 'sell', 50000.0, 100.0, 0.8)
        sell_result = executor.execute_signal_order(sell_signal, 0.1)
        
        # Buy should be slightly higher, sell slightly lower (due to slippage)
        assert buy_result.fill_price >= 50000.0
        assert sell_result.fill_price <= 50000.0
    
    @patch('execution.ccxt.binance')
    def test_real_order_execution_success(self, mock_binance):
        """Test successful real order execution"""
        # Setup mock exchange
        mock_exchange = MagicMock()
        mock_exchange.create_market_order.return_value = {'id': 'order_123'}
        mock_exchange.fetch_order.return_value = {
            'id': 'order_123',
            'status': 'closed',
            'average': 50100.0,
            'filled': 0.1
        }
        mock_binance.return_value = mock_exchange
        
        executor = OrderExecutor(self.api_key, self.api_secret, paper_trading=False)
        signal = TradingSignal('Test Trader', 'BTC/USDT', 'buy', 50000.0, 100.0, 0.8)
        
        result = executor.execute_signal_order(signal, 0.1)
        
        assert result.success is True
        assert result.order_id == 'order_123'
        assert result.fill_price == 50100.0
        assert result.fill_amount == 0.1
        
        mock_exchange.create_market_order.assert_called_once_with(
            symbol='BTC/USDT',
            side='buy',
            amount=0.1
        )
    
    @patch('execution.ccxt.binance')
    def test_real_order_insufficient_funds(self, mock_binance):
        """Test order execution with insufficient funds"""
        mock_exchange = MagicMock()
        mock_exchange.create_market_order.side_effect = ccxt.InsufficientFunds('Not enough balance')
        mock_binance.return_value = mock_exchange
        
        executor = OrderExecutor(self.api_key, self.api_secret, paper_trading=False)
        signal = TradingSignal('Test Trader', 'BTC/USDT', 'buy', 50000.0, 100.0, 0.8)
        
        result = executor.execute_signal_order(signal, 0.1)
        
        assert result.success is False
        assert 'Insufficient funds' in result.error
    
    @patch('execution.ccxt.binance')
    @patch('execution.time.sleep')
    def test_real_order_network_retry(self, mock_sleep, mock_binance):
        """Test order execution with network error and retry"""
        mock_exchange = MagicMock()
        # First two attempts fail with network error, third succeeds
        mock_exchange.create_market_order.side_effect = [
            ccxt.NetworkError('Connection timeout'),
            ccxt.NetworkError('Connection timeout'),
            {'id': 'order_123'}
        ]
        mock_exchange.fetch_order.return_value = {
            'id': 'order_123',
            'status': 'closed',
            'average': 50100.0,
            'filled': 0.1
        }
        mock_binance.return_value = mock_exchange
        
        executor = OrderExecutor(self.api_key, self.api_secret, paper_trading=False)
        signal = TradingSignal('Test Trader', 'BTC/USDT', 'buy', 50000.0, 100.0, 0.8)
        
        result = executor.execute_signal_order(signal, 0.1)
        
        assert result.success is True
        assert result.order_id == 'order_123'
        assert mock_exchange.create_market_order.call_count == 3  # 2 retries + success
        assert mock_sleep.call_count >= 2  # Should sleep between retries
    
    @patch('execution.ccxt.binance')
    def test_real_order_max_retries_exceeded(self, mock_binance):
        """Test order execution when max retries are exceeded"""
        mock_exchange = MagicMock()
        mock_exchange.create_market_order.side_effect = ccxt.NetworkError('Connection timeout')
        mock_binance.return_value = mock_exchange
        
        executor = OrderExecutor(self.api_key, self.api_secret, paper_trading=False)
        signal = TradingSignal('Test Trader', 'BTC/USDT', 'buy', 50000.0, 100.0, 0.8)
        
        result = executor.execute_signal_order(signal, 0.1)
        
        assert result.success is False
        assert 'Network error' in result.error
        assert mock_exchange.create_market_order.call_count == 3  # Max retries
    
    def test_paper_stop_loss_creation(self):
        """Test paper trading stop loss order creation"""
        executor = OrderExecutor(self.api_key, self.api_secret, paper_trading=True)
        
        result = executor.create_stop_loss_order('BTC/USDT', 'buy', 0.1, 49000.0)
        
        assert result.success is True
        assert 'PAPER_SL_' in result.order_id
        assert result.fill_price == 49000.0
        assert result.fill_amount == 0.1
    
    @patch('execution.ccxt.binance')
    def test_real_stop_loss_creation(self, mock_binance):
        """Test real stop loss order creation"""
        mock_exchange = MagicMock()
        mock_exchange.create_order.return_value = {'id': 'stop_order_123'}
        mock_binance.return_value = mock_exchange
        
        executor = OrderExecutor(self.api_key, self.api_secret, paper_trading=False)
        
        result = executor.create_stop_loss_order('BTC/USDT', 'buy', 0.1, 49000.0)
        
        assert result.success is True
        assert result.order_id == 'stop_order_123'
        
        # Should create sell order for buy position (opposite side)
        mock_exchange.create_order.assert_called_once_with(
            symbol='BTC/USDT',
            type='stop_market',
            side='sell',  # Opposite of position side
            amount=0.1,
            params={'stopPrice': 49000.0}
        )
    
    def test_paper_order_cancellation(self):
        """Test paper trading order cancellation"""
        executor = OrderExecutor(self.api_key, self.api_secret, paper_trading=True)
        
        success = executor.cancel_order('PAPER_ORDER_123', 'BTC/USDT')
        assert success is True
    
    @patch('execution.ccxt.binance')
    def test_real_order_cancellation(self, mock_binance):
        """Test real order cancellation"""
        mock_exchange = MagicMock()
        mock_exchange.cancel_order.return_value = None
        mock_binance.return_value = mock_exchange
        
        executor = OrderExecutor(self.api_key, self.api_secret, paper_trading=False)
        
        success = executor.cancel_order('order_123', 'BTC/USDT')
        
        assert success is True
        mock_exchange.cancel_order.assert_called_once_with('order_123', 'BTC/USDT')
    
    def test_paper_current_price(self):
        """Test paper trading current price simulation"""
        executor = OrderExecutor(self.api_key, self.api_secret, paper_trading=True)
        
        btc_price = executor.get_current_price('BTC/USDT')
        eth_price = executor.get_current_price('ETH/USDT')
        
        assert btc_price is not None
        assert eth_price is not None
        assert btc_price > 40000  # Reasonable BTC price range
        assert btc_price < 70000
        assert eth_price > 2000   # Reasonable ETH price range
        assert eth_price < 5000
    
    @patch('execution.ccxt.binance')
    def test_real_current_price(self, mock_binance):
        """Test real current price fetching"""
        mock_exchange = MagicMock()
        mock_exchange.fetch_ticker.return_value = {'last': 50000.0}
        mock_binance.return_value = mock_exchange
        
        executor = OrderExecutor(self.api_key, self.api_secret, paper_trading=False)
        
        price = executor.get_current_price('BTC/USDT')
        
        assert price == 50000.0
        mock_exchange.fetch_ticker.assert_called_once_with('BTC/USDT')
    
    def test_paper_account_balance(self):
        """Test paper trading account balance"""
        executor = OrderExecutor(self.api_key, self.api_secret, paper_trading=True)
        
        balance = executor.get_account_balance()
        
        assert isinstance(balance, dict)
        assert 'USDT' in balance
        assert balance['USDT'] == 10000.0  # Default paper trading balance
        assert 'BTC' in balance
        assert 'ETH' in balance
    
    @patch('execution.ccxt.binance')
    def test_real_account_balance(self, mock_binance):
        """Test real account balance fetching"""
        mock_exchange = MagicMock()
        mock_exchange.fetch_balance.return_value = {
            'USDT': {'free': 5000.0},
            'BTC': {'free': 0.1},
            'ETH': {'free': 0.0}  # Zero balance should be filtered out
        }
        mock_binance.return_value = mock_exchange
        
        executor = OrderExecutor(self.api_key, self.api_secret, paper_trading=False)
        
        balance = executor.get_account_balance()
        
        assert balance['USDT'] == 5000.0
        assert balance['BTC'] == 0.1
        assert 'ETH' not in balance  # Zero balance filtered out
    
    def test_order_execution_flow(self):
        """Test complete order execution flow in paper mode"""
        executor = OrderExecutor(self.api_key, self.api_secret, paper_trading=True)
        
        # Execute main order
        signal = TradingSignal('Test Trader', 'BTC/USDT', 'buy', 50000.0, 100.0, 0.8)
        order_result = executor.execute_signal_order(signal, 0.1)
        
        assert order_result.success is True
        
        # Create stop loss
        stop_result = executor.create_stop_loss_order(
            'BTC/USDT', 'buy', order_result.fill_amount, 49000.0
        )
        
        assert stop_result.success is True
        
        # Get current price
        current_price = executor.get_current_price('BTC/USDT')
        assert current_price is not None
        
        # Check balance
        balance = executor.get_account_balance()
        assert balance['USDT'] > 0