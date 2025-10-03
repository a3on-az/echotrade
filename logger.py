"""
Centralized logging configuration for EchoTrade
"""
import logging
import logging.handlers
import os
from datetime import datetime
from config import Config

def setup_logging(log_level: str = None, log_file: str = None):
    """Configure logging for EchoTrade with file and console output"""
    
    log_level = log_level or Config.LOG_LEVEL
    log_file = log_file or Config.LOG_FILE
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(log_file) if os.path.dirname(log_file) else 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    # Convert string log level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)  # File gets all messages
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Suppress noisy external library logs
    logging.getLogger('ccxt').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    # Create application loggers
    app_logger = logging.getLogger('echotrade')
    signals_logger = logging.getLogger('echotrade.signals')
    risk_logger = logging.getLogger('echotrade.risk')
    execution_logger = logging.getLogger('echotrade.execution')
    
    app_logger.info("EchoTrade logging configured")
    app_logger.info(f"Log level: {log_level}")
    app_logger.info(f"Log file: {log_file}")
    
    return app_logger

def get_logger(name: str = 'echotrade'):
    """Get a logger instance"""
    return logging.getLogger(name)

# Create a trading-specific log file for important events
def log_trade_event(event_type: str, symbol: str, details: dict):
    """Log important trading events to a separate trade log"""
    trade_logger = logging.getLogger('echotrade.trades')
    
    # Create a structured log message
    message = f"[{event_type}] {symbol} - {details}"
    
    if event_type in ['ORDER_EXECUTED', 'POSITION_OPENED']:
        trade_logger.info(message)
    elif event_type in ['STOP_LOSS_TRIGGERED', 'POSITION_CLOSED']:
        trade_logger.warning(message)
    elif event_type in ['ORDER_FAILED', 'RISK_VIOLATION']:
        trade_logger.error(message)
    else:
        trade_logger.info(message)