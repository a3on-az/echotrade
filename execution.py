import logging
import ccxt
import time
from typing import Dict, Optional, Any, Tuple
from config import Config
from signals import TradingSignal

logger = logging.getLogger(__name__)

class OrderResult:
    """Result of an order execution"""
    
    def __init__(self, success: bool, order_id: str = None, fill_price: float = None,
                 fill_amount: float = None, error: str = None):
        self.success = success
        self.order_id = order_id
        self.fill_price = fill_price
        self.fill_amount = fill_amount
        self.error = error
        self.timestamp = time.time()

class OrderExecutor:
    """Handles order execution with retry logic and proper error handling"""
    
    def __init__(self, api_key: str, api_secret: str, sandbox: bool = True, paper_trading: bool = False):
        self.paper_trading = paper_trading
        
        if not paper_trading:
            # Initialize real exchange connection
            exchange_config = {
                'apiKey': api_key,
                'secret': api_secret,
                'timeout': Config.ORDER_TIMEOUT * 1000,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot'
                }
            }
            
            if sandbox:
                exchange_config['sandbox'] = True
                
            self.exchange = ccxt.binance(exchange_config)
        else:
            self.exchange = None
            logger.info("OrderExecutor initialized in paper trading mode")
            
        self.retry_attempts = 3
        self.retry_delay = 1.0  # seconds
    
    def _simulate_order_execution(self, signal: TradingSignal, amount: float) -> OrderResult:
        """Simulate order execution for paper trading"""
        # Simulate some slippage (0.01-0.05%)
        import random
        slippage = random.uniform(0.0001, 0.0005)
        
        if signal.side == 'buy':
            fill_price = signal.price * (1 + slippage)
        else:
            fill_price = signal.price * (1 - slippage)
            
        # Simulate partial fills occasionally
        fill_amount = amount * random.uniform(0.95, 1.0)
        
        fake_order_id = f"PAPER_{int(time.time())}_{signal.symbol.replace('/', '')}"
        
        logger.info(f"[PAPER] Simulated {signal.side} order: {fill_amount:.6f} {signal.symbol} @ {fill_price:.2f}")
        
        return OrderResult(
            success=True,
            order_id=fake_order_id,
            fill_price=fill_price,
            fill_amount=fill_amount
        )
    
    def _execute_market_order_with_retry(self, signal: TradingSignal, amount: float) -> OrderResult:
        """Execute market order with retry logic"""
        for attempt in range(self.retry_attempts):
            try:
                # Create market order
                order = self.exchange.create_market_order(
                    symbol=signal.symbol,
                    side=signal.side,
                    amount=amount
                )
                
                # Wait a bit for order to be filled
                time.sleep(0.5)
                
                # Fetch order status to get fill information
                order_status = self.exchange.fetch_order(order['id'], signal.symbol)
                
                if order_status['status'] == 'closed':
                    return OrderResult(
                        success=True,
                        order_id=order['id'],
                        fill_price=order_status['average'] or order_status['price'],
                        fill_amount=order_status['filled']
                    )
                else:
                    logger.warning(f"Order not immediately filled, status: {order_status['status']}")
                    return OrderResult(
                        success=False,
                        error=f"Order not filled, status: {order_status['status']}"
                    )
                    
            except ccxt.InsufficientFunds as e:
                logger.error(f"Insufficient funds for order: {e}")
                return OrderResult(success=False, error="Insufficient funds")
                
            except ccxt.InvalidOrder as e:
                logger.error(f"Invalid order parameters: {e}")
                return OrderResult(success=False, error=f"Invalid order: {e}")
                
            except ccxt.NetworkError as e:
                logger.warning(f"Network error (attempt {attempt + 1}/{self.retry_attempts}): {e}")
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                else:
                    return OrderResult(success=False, error=f"Network error: {e}")
                    
            except ccxt.ExchangeError as e:
                logger.error(f"Exchange error: {e}")
                return OrderResult(success=False, error=f"Exchange error: {e}")
                
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                if attempt < self.retry_attempts - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                else:
                    return OrderResult(success=False, error=f"Unexpected error: {e}")
        
        return OrderResult(success=False, error="Max retry attempts exceeded")
    
    def execute_signal_order(self, signal: TradingSignal, amount: float) -> OrderResult:
        """Execute an order based on a trading signal"""
        logger.info(f"Executing {signal.side} order: {amount:.6f} {signal.symbol} @ ~{signal.price:.2f}")
        
        # Paper trading simulation
        if self.paper_trading:
            return self._simulate_order_execution(signal, amount)
        
        # Real order execution
        return self._execute_market_order_with_retry(signal, amount)
    
    def create_stop_loss_order(self, symbol: str, side: str, amount: float, stop_price: float) -> OrderResult:
        """Create a stop-loss order"""
        if self.paper_trading:
            logger.info(f"[PAPER] Stop-loss order created: {side} {amount:.6f} {symbol} @ stop {stop_price:.2f}")
            return OrderResult(
                success=True,
                order_id=f"PAPER_SL_{int(time.time())}_{symbol.replace('/', '')}",
                fill_price=stop_price,
                fill_amount=amount
            )
        
        try:
            # Create stop-loss order
            # Note: Binance uses 'stopPrice' in params for stop orders
            opposite_side = 'sell' if side == 'buy' else 'buy'
            
            order = self.exchange.create_order(
                symbol=symbol,
                type='stop_market',
                side=opposite_side,  # Stop-loss for long position = sell order
                amount=amount,
                params={'stopPrice': stop_price}
            )
            
            logger.info(f"Stop-loss order created: {order['id']} for {symbol}")
            return OrderResult(
                success=True,
                order_id=order['id'],
                fill_price=stop_price,
                fill_amount=amount
            )
            
        except Exception as e:
            logger.error(f"Error creating stop-loss order: {e}")
            return OrderResult(success=False, error=f"Stop-loss order failed: {e}")
    
    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an existing order"""
        if self.paper_trading:
            logger.info(f"[PAPER] Cancelled order: {order_id}")
            return True
            
        try:
            self.exchange.cancel_order(order_id, symbol)
            logger.info(f"Cancelled order: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current market price for a symbol"""
        if self.paper_trading:
            # For paper trading, simulate price with some randomness
            import random
            base_price = 50000 if 'BTC' in symbol else 3000  # Rough estimates
            return base_price * random.uniform(0.95, 1.05)
            
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker['last']
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            return None
    
    def get_account_balance(self) -> Dict[str, float]:
        """Get current account balance"""
        if self.paper_trading:
            # Return simulated balance for paper trading
            return {
                'USDT': 10000.0,
                'BTC': 0.0,
                'ETH': 0.0,
                'BNB': 0.0
            }
            
        try:
            balance = self.exchange.fetch_balance()
            return {currency: info['free'] for currency, info in balance.items() if info['free'] > 0}
        except Exception as e:
            logger.error(f"Error fetching account balance: {e}")
            return {}
