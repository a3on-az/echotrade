import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from config import Config
from signals import TradingSignal

logger = logging.getLogger(__name__)

class PositionInfo:
    """Information about an open position"""
    
    def __init__(self, symbol: str, side: str, size: float, entry_price: float, 
                 stop_loss: float, timestamp: datetime):
        self.symbol = symbol
        self.side = side
        self.size = size
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.timestamp = timestamp
        self.current_pnl = 0.0
        
    def update_pnl(self, current_price: float):
        """Update current P&L based on current market price"""
        if self.side == 'buy':
            self.current_pnl = (current_price - self.entry_price) * self.size
        else:  # sell
            self.current_pnl = (self.entry_price - current_price) * self.size
            
        return self.current_pnl

class RiskManager:
    """Comprehensive risk management for EchoTrade"""
    
    def __init__(self, portfolio_value: float = None):
        self.portfolio_value = portfolio_value or Config.PORTFOLIO_VALUE
        self.risk_params = Config.get_risk_params()
        self.open_positions: Dict[str, PositionInfo] = {}
        self.daily_pnl = 0.0
        self.max_drawdown = 0.0
        self.peak_portfolio_value = self.portfolio_value
        self.trades_today = 0
        self.last_reset_date = datetime.now().date()
        
    def reset_daily_stats(self):
        """Reset daily statistics if it's a new day"""
        current_date = datetime.now().date()
        if current_date > self.last_reset_date:
            self.trades_today = 0
            self.daily_pnl = 0.0
            self.last_reset_date = current_date
            logger.info("Daily statistics reset")
            
    def calculate_position_size(self, signal: TradingSignal, current_price: float = None) -> float:
        """Calculate position size based on risk parameters and signal confidence"""
        if current_price is None:
            current_price = signal.price
            
        # Base position size as percentage of portfolio
        base_position_value = self.portfolio_value * self.risk_params['position_size_percent']
        
        # Adjust by signal confidence
        adjusted_position_value = base_position_value * signal.confidence
        
        # Calculate position size in base currency units
        position_size = adjusted_position_value / current_price
        
        # Apply minimum trade amount check
        if adjusted_position_value < self.risk_params['min_trade_amount']:
            logger.warning(f"Position size {adjusted_position_value} below minimum {self.risk_params['min_trade_amount']}")
            return 0.0
            
        return position_size
    
    def calculate_stop_loss_price(self, entry_price: float, side: str) -> float:
        """Calculate stop loss price based on entry price and side"""
        stop_loss_multiplier = 1 - self.risk_params['stop_loss_percent']
        
        if side == 'buy':
            # For long positions, stop loss is below entry price
            return entry_price * stop_loss_multiplier
        else:
            # For short positions, stop loss is above entry price
            return entry_price / stop_loss_multiplier
    
    def check_position_limits(self) -> bool:
        """Check if we can open new positions based on limits"""
        # Check maximum concurrent positions
        if len(self.open_positions) >= self.risk_params['max_concurrent_positions']:
            logger.warning(f"Maximum concurrent positions ({self.risk_params['max_concurrent_positions']}) reached")
            return False
            
        return True
    
    def check_drawdown_limit(self) -> bool:
        """Check if current drawdown is within acceptable limits"""
        current_portfolio_value = self.calculate_current_portfolio_value()
        
        # Update peak value
        if current_portfolio_value > self.peak_portfolio_value:
            self.peak_portfolio_value = current_portfolio_value
        
        # Calculate current drawdown
        current_drawdown = (self.peak_portfolio_value - current_portfolio_value) / self.peak_portfolio_value
        
        if current_drawdown > self.max_drawdown:
            self.max_drawdown = current_drawdown
            
        # Check if drawdown exceeds limit
        if current_drawdown > self.risk_params['max_drawdown_percent']:
            logger.critical(f"Drawdown limit exceeded: {current_drawdown:.2%} > {self.risk_params['max_drawdown_percent']:.2%}")
            return False
            
        return True
    
    def calculate_current_portfolio_value(self) -> float:
        """Calculate current portfolio value including open positions"""
        total_pnl = sum(pos.current_pnl for pos in self.open_positions.values())
        return self.portfolio_value + total_pnl
    
    def validate_signal(self, signal: TradingSignal) -> Tuple[bool, str]:
        """Comprehensive signal validation"""
        self.reset_daily_stats()
        
        # Check basic signal validity
        if signal.confidence < 0.1:
            return False, "Signal confidence too low"
        
        if signal.symbol not in Config.TRADING_PAIRS:
            return False, f"Symbol {signal.symbol} not in allowed trading pairs"
        
        # Check position limits
        if not self.check_position_limits():
            return False, "Position limits exceeded"
        
        # Check drawdown limits
        if not self.check_drawdown_limit():
            return False, "Drawdown limit exceeded"
        
        # Check if we already have a position in this symbol
        if signal.symbol in self.open_positions:
            existing_pos = self.open_positions[signal.symbol]
            if existing_pos.side == signal.side:
                return False, f"Already have {signal.side} position in {signal.symbol}"
        
        # Calculate proposed position size
        position_size = self.calculate_position_size(signal)
        if position_size == 0.0:
            return False, "Position size too small"
        
        # Check if position value exceeds single trade limit
        position_value = position_size * signal.price
        max_single_trade = self.portfolio_value * 0.1  # Max 10% per trade
        if position_value > max_single_trade:
            return False, f"Position value {position_value:.2f} exceeds single trade limit {max_single_trade:.2f}"
        
        return True, "Signal validation passed"
    
    def add_position(self, signal: TradingSignal, actual_fill_price: float, 
                    actual_size: float) -> bool:
        """Add a new position to tracking"""
        stop_loss_price = self.calculate_stop_loss_price(actual_fill_price, signal.side)
        
        position = PositionInfo(
            symbol=signal.symbol,
            side=signal.side,
            size=actual_size,
            entry_price=actual_fill_price,
            stop_loss=stop_loss_price,
            timestamp=datetime.now()
        )
        
        self.open_positions[signal.symbol] = position
        self.trades_today += 1
        
        logger.info(f"Added position: {signal.symbol} {signal.side} {actual_size:.6f} @ {actual_fill_price:.2f}")
        return True
    
    def remove_position(self, symbol: str, exit_price: float) -> Optional[float]:
        """Remove a position and calculate P&L"""
        if symbol not in self.open_positions:
            return None
            
        position = self.open_positions[symbol]
        final_pnl = position.update_pnl(exit_price)
        
        # Update portfolio value and daily P&L
        self.portfolio_value += final_pnl
        self.daily_pnl += final_pnl
        
        del self.open_positions[symbol]
        
        logger.info(f"Closed position: {symbol} with P&L: {final_pnl:.2f}")
        return final_pnl
    
    def update_positions(self, market_prices: Dict[str, float]):
        """Update all open positions with current market prices"""
        for symbol, position in self.open_positions.items():
            if symbol in market_prices:
                position.update_pnl(market_prices[symbol])
    
    def check_stop_losses(self, market_prices: Dict[str, float]) -> List[str]:
        """Check which positions should be closed due to stop loss"""
        symbols_to_close = []
        
        for symbol, position in self.open_positions.items():
            if symbol not in market_prices:
                continue
                
            current_price = market_prices[symbol]
            
            # Check stop loss condition
            should_close = False
            if position.side == 'buy' and current_price <= position.stop_loss:
                should_close = True
            elif position.side == 'sell' and current_price >= position.stop_loss:
                should_close = True
                
            if should_close:
                symbols_to_close.append(symbol)
                logger.warning(f"Stop loss triggered for {symbol} at {current_price:.2f}")
                
        return symbols_to_close
    
    def get_risk_summary(self) -> Dict:
        """Get current risk summary"""
        current_value = self.calculate_current_portfolio_value()
        current_drawdown = max(0, (self.peak_portfolio_value - current_value) / self.peak_portfolio_value)
        
        return {
            'portfolio_value': current_value,
            'daily_pnl': self.daily_pnl,
            'open_positions': len(self.open_positions),
            'max_drawdown': self.max_drawdown,
            'current_drawdown': current_drawdown,
            'trades_today': self.trades_today,
            'position_details': {
                symbol: {
                    'side': pos.side,
                    'size': pos.size,
                    'entry_price': pos.entry_price,
                    'current_pnl': pos.current_pnl,
                    'stop_loss': pos.stop_loss
                } for symbol, pos in self.open_positions.items()
            }
        }
