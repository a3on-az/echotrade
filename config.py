import os
from dotenv import load_dotenv
from typing import List, Dict, Any

# Load environment variables
load_dotenv()

class Config:
    """EchoTrade configuration management"""
    
    # API Configuration
    API_KEY = os.getenv('BINANCE_API_KEY', '')
    API_SECRET = os.getenv('BINANCE_API_SECRET', '')
    SANDBOX_MODE = os.getenv('SANDBOX_MODE', 'True').lower() == 'true'
    
    # Trading Configuration
    PORTFOLIO_VALUE = float(os.getenv('PORTFOLIO_VALUE', '10000'))
    POSITION_SIZE_PERCENT = float(os.getenv('POSITION_SIZE_PERCENT', '2.0'))  # 2%
    STOP_LOSS_PERCENT = float(os.getenv('STOP_LOSS_PERCENT', '2.0'))  # 2%
    MAX_DRAWDOWN_PERCENT = float(os.getenv('MAX_DRAWDOWN_PERCENT', '30.0'))  # 30%
    
    # Copy Trading Configuration
    TARGET_TRADERS = [
        {
            'name': 'Yun Qiang',
            'roi_30d': 1700.0,  # +1700% 30d ROI
            'priority': 1
        },
        {
            'name': 'Crypto Loby',
            'roi_30d': 850.0,   # Example ROI
            'priority': 2
        }
    ]
    
    # Trading Pairs
    TRADING_PAIRS = [
        'BTC/USDT',
        'ETH/USDT',
        'BNB/USDT',
        'ADA/USDT'
    ]
    
    # Risk Management
    MIN_TRADE_AMOUNT = float(os.getenv('MIN_TRADE_AMOUNT', '10.0'))  # USDT
    MAX_CONCURRENT_POSITIONS = int(os.getenv('MAX_CONCURRENT_POSITIONS', '5'))
    
    # Timing Configuration
    SIGNAL_CHECK_INTERVAL = int(os.getenv('SIGNAL_CHECK_INTERVAL', '60'))  # seconds
    ORDER_TIMEOUT = int(os.getenv('ORDER_TIMEOUT', '30'))  # seconds
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'echotrade.log')
    
    @classmethod
    def validate_config(cls) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []
        
        if not cls.API_KEY:
            errors.append("BINANCE_API_KEY not set")
        if not cls.API_SECRET:
            errors.append("BINANCE_API_SECRET not set")
        if cls.PORTFOLIO_VALUE <= 0:
            errors.append("PORTFOLIO_VALUE must be positive")
        if not (0 < cls.POSITION_SIZE_PERCENT <= 10):
            errors.append("POSITION_SIZE_PERCENT must be between 0 and 10")
        if not (0 < cls.STOP_LOSS_PERCENT <= 20):
            errors.append("STOP_LOSS_PERCENT must be between 0 and 20")
            
        return errors
    
    @classmethod
    def get_risk_params(cls) -> Dict[str, Any]:
        """Get risk management parameters"""
        return {
            'position_size_percent': cls.POSITION_SIZE_PERCENT / 100,
            'stop_loss_percent': cls.STOP_LOSS_PERCENT / 100,
            'max_drawdown_percent': cls.MAX_DRAWDOWN_PERCENT / 100,
            'min_trade_amount': cls.MIN_TRADE_AMOUNT,
            'max_concurrent_positions': cls.MAX_CONCURRENT_POSITIONS
        }

# Backward compatibility
API_KEY = Config.API_KEY
API_SECRET = Config.API_SECRET
TRADERS = [trader['name'] for trader in Config.TARGET_TRADERS]
PAIRS = Config.TRADING_PAIRS
