#!/usr/bin/env python3
"""
EchoTrade - Crypto Copy Trading Bot

Mirrors high-ROI Binance traders with comprehensive risk management.
Focus on profitability with proper position sizing and stop losses.
"""

import argparse
import time
import signal
import sys
from typing import Dict, List
from datetime import datetime

# Import EchoTrade modules
from config import Config
from signals import SignalFetcher, TradingSignal
from risk import RiskManager
from execution import OrderExecutor, OrderResult
from logger import setup_logging, get_logger, log_trade_event

class EchoTradeBot:
    """Main EchoTrade bot orchestrator"""
    
    def __init__(self, paper_trading: bool = True, log_level: str = 'INFO'):
        # Setup logging first
        setup_logging(log_level=log_level)
        self.logger = get_logger('echotrade.main')
        
        # Validate configuration
        config_errors = Config.validate_config()
        if config_errors and not paper_trading:
            for error in config_errors:
                self.logger.error(f"Configuration error: {error}")
            raise ValueError("Configuration validation failed")
        
        self.paper_trading = paper_trading
        self.running = False
        
        # Initialize components
        self.signal_fetcher = SignalFetcher(
            api_key=Config.API_KEY,
            api_secret=Config.API_SECRET,
            sandbox=Config.SANDBOX_MODE
        )
        
        self.risk_manager = RiskManager(Config.PORTFOLIO_VALUE)
        
        self.order_executor = OrderExecutor(
            api_key=Config.API_KEY,
            api_secret=Config.API_SECRET,
            sandbox=Config.SANDBOX_MODE,
            paper_trading=paper_trading
        )
        
        self.logger.info(f"EchoTrade initialized - Paper Trading: {paper_trading}")
        self.logger.info(f"Portfolio Value: ${Config.PORTFOLIO_VALUE:,.2f}")
        self.logger.info(f"Target Traders: {[t['name'] for t in Config.TARGET_TRADERS]}")
        self.logger.info(f"Trading Pairs: {Config.TRADING_PAIRS}")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.logger.info("Shutdown signal received, stopping bot...")
        self.running = False
    
    def process_signals(self, signals: List[TradingSignal]):
        """Process trading signals and execute trades"""
        if not signals:
            self.logger.debug("No signals to process")
            return
            
        self.logger.info(f"Processing {len(signals)} signals")
        
        # Group signals by symbol for analysis
        signals_by_symbol = {}
        for signal in signals:
            if signal.symbol not in signals_by_symbol:
                signals_by_symbol[signal.symbol] = []
            signals_by_symbol[signal.symbol].append(signal)
        
        for symbol, symbol_signals in signals_by_symbol.items():
            try:
                self.process_symbol_signals(symbol, symbol_signals)
            except Exception as e:
                self.logger.error(f"Error processing signals for {symbol}: {e}")
    
    def process_symbol_signals(self, symbol: str, signals: List[TradingSignal]):
        """Process all signals for a specific symbol"""
        # Analyze signal strength
        signal_strength = self.signal_fetcher.get_signal_strength(signals, symbol)
        
        self.logger.debug(f"{symbol} signal analysis: {signal_strength}")
        
        # Only act on strong signals
        min_signal_strength = 0.3
        net_sentiment = signal_strength['net_sentiment']
        
        if abs(net_sentiment) < min_signal_strength:
            self.logger.debug(f"Signal strength too weak for {symbol}: {net_sentiment:.3f}")
            return
        
        # Determine dominant signal direction
        dominant_side = 'buy' if net_sentiment > 0 else 'sell'
        dominant_signals = [s for s in signals if s.side == dominant_side]
        
        if not dominant_signals:
            return
        
        # Use the highest confidence signal
        best_signal = max(dominant_signals, key=lambda s: s.confidence)
        
        # Validate signal with risk management
        is_valid, reason = self.risk_manager.validate_signal(best_signal)
        
        if not is_valid:
            self.logger.warning(f"Signal rejected for {symbol}: {reason}")
            log_trade_event('SIGNAL_REJECTED', symbol, {'reason': reason, 'signal': str(best_signal)})
            return
        
        # Calculate position size
        position_size = self.risk_manager.calculate_position_size(best_signal)
        
        if position_size <= 0:
            self.logger.warning(f"Position size too small for {symbol}: {position_size}")
            return
        
        # Execute the trade
        self.execute_trade(best_signal, position_size)
    
    def execute_trade(self, signal: TradingSignal, position_size: float):
        """Execute a trade based on validated signal"""
        self.logger.info(f"Executing trade: {signal.side} {position_size:.6f} {signal.symbol} @ ~{signal.price:.2f}")
        
        # Execute the order
        order_result = self.order_executor.execute_signal_order(signal, position_size)
        
        if not order_result.success:
            self.logger.error(f"Order execution failed: {order_result.error}")
            log_trade_event('ORDER_FAILED', signal.symbol, {
                'error': order_result.error,
                'signal': str(signal),
                'position_size': position_size
            })
            return
        
        # Add position to risk manager
        self.risk_manager.add_position(signal, order_result.fill_price, order_result.fill_amount)
        
        # Create stop-loss order
        stop_loss_price = self.risk_manager.calculate_stop_loss_price(order_result.fill_price, signal.side)
        stop_loss_result = self.order_executor.create_stop_loss_order(
            signal.symbol, signal.side, order_result.fill_amount, stop_loss_price
        )
        
        # Log the trade
        log_trade_event('POSITION_OPENED', signal.symbol, {
            'side': signal.side,
            'size': order_result.fill_amount,
            'entry_price': order_result.fill_price,
            'stop_loss': stop_loss_price,
            'confidence': signal.confidence,
            'trader': signal.trader_name
        })
        
        self.logger.info(f"Position opened: {signal.symbol} {signal.side} {order_result.fill_amount:.6f} @ {order_result.fill_price:.2f}")
        if stop_loss_result.success:
            self.logger.info(f"Stop-loss set at {stop_loss_price:.2f}")
    
    def check_stop_losses(self):
        """Check and execute stop losses"""
        if not self.risk_manager.open_positions:
            return
            
        # Get current market prices
        market_prices = {}
        for symbol in self.risk_manager.open_positions.keys():
            price = self.order_executor.get_current_price(symbol)
            if price:
                market_prices[symbol] = price
        
        # Update positions with current prices
        self.risk_manager.update_positions(market_prices)
        
        # Check for stop loss triggers
        symbols_to_close = self.risk_manager.check_stop_losses(market_prices)
        
        for symbol in symbols_to_close:
            self.close_position(symbol, market_prices[symbol], 'STOP_LOSS')
    
    def close_position(self, symbol: str, exit_price: float, reason: str = 'MANUAL'):
        """Close a position"""
        position = self.risk_manager.open_positions.get(symbol)
        if not position:
            return
            
        # Execute closing order (opposite side)
        close_side = 'sell' if position.side == 'buy' else 'buy'
        close_signal = TradingSignal(
            trader_name='SYSTEM',
            symbol=symbol,
            side=close_side,
            price=exit_price,
            amount=position.size
        )
        
        order_result = self.order_executor.execute_signal_order(close_signal, position.size)
        
        if order_result.success:
            # Remove position and calculate P&L
            pnl = self.risk_manager.remove_position(symbol, order_result.fill_price)
            
            log_trade_event('POSITION_CLOSED', symbol, {
                'side': position.side,
                'size': position.size,
                'entry_price': position.entry_price,
                'exit_price': order_result.fill_price,
                'pnl': pnl,
                'reason': reason
            })
            
            self.logger.info(f"Position closed: {symbol} P&L: ${pnl:.2f} ({reason})")
        else:
            self.logger.error(f"Failed to close position {symbol}: {order_result.error}")
    
    def print_status(self):
        """Print current bot status"""
        risk_summary = self.risk_manager.get_risk_summary()
        
        print("\n" + "="*60)
        print(f"EchoTrade Status - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        print(f"Portfolio Value:     ${risk_summary['portfolio_value']:,.2f}")
        print(f"Daily P&L:           ${risk_summary['daily_pnl']:+,.2f}")
        print(f"Open Positions:      {risk_summary['open_positions']}")
        print(f"Current Drawdown:    {risk_summary['current_drawdown']:.1%}")
        print(f"Max Drawdown:        {risk_summary['max_drawdown']:.1%}")
        print(f"Trades Today:        {risk_summary['trades_today']}")
        
        if risk_summary['position_details']:
            print("\nOpen Positions:")
            for symbol, pos in risk_summary['position_details'].items():
                print(f"  {symbol}: {pos['side']} {pos['size']:.6f} @ {pos['entry_price']:.2f} (P&L: ${pos['current_pnl']:+.2f})")
        
        print("="*60)
    
    def run(self, max_iterations: int = None):
        """Main bot loop"""
        self.logger.info("Starting EchoTrade bot...")
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        self.running = True
        iteration = 0
        
        try:
            while self.running:
                iteration += 1
                
                if max_iterations and iteration > max_iterations:
                    self.logger.info(f"Max iterations ({max_iterations}) reached")
                    break
                
                self.logger.debug(f"Iteration {iteration} starting")
                
                try:
                    # Fetch and process signals
                    signals = self.signal_fetcher.fetch_signals()
                    self.process_signals(signals)
                    
                    # Check stop losses
                    self.check_stop_losses()
                    
                    # Print status every 10 iterations
                    if iteration % 10 == 0:
                        self.print_status()
                    
                except Exception as e:
                    self.logger.error(f"Error in main loop iteration {iteration}: {e}")
                
                # Wait before next iteration
                time.sleep(Config.SIGNAL_CHECK_INTERVAL)
                
        except KeyboardInterrupt:
            self.logger.info("Bot stopped by user")
        except Exception as e:
            self.logger.error(f"Unexpected error in main loop: {e}")
        finally:
            self.logger.info("EchoTrade bot stopped")
            self.print_status()

def main():
    parser = argparse.ArgumentParser(description='EchoTrade - Crypto Copy Trading Bot')
    parser.add_argument('--paper', action='store_true', help='Run in paper trading mode')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Set logging level')
    parser.add_argument('--max-iterations', type=int, help='Maximum number of iterations (for testing)')
    parser.add_argument('--status', action='store_true', help='Show current status and exit')
    
    args = parser.parse_args()
    
    try:
        # Create bot instance
        bot = EchoTradeBot(paper_trading=args.paper, log_level=args.log_level)
        
        if args.status:
            # Just show status and exit
            bot.print_status()
            return
        
        # Run the bot
        bot.run(max_iterations=args.max_iterations)
        
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
