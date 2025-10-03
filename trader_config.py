#!/usr/bin/env python3
"""
Trader Configuration & Management
Data models and persistence for trader settings
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class TraderConfig:
    """Configuration for a single trader"""

    # Identity
    id: str
    name: str
    source: str  # 'binance', 'telegram', 'manual'

    # Status
    active: bool = True
    paper_trade_only: bool = True  # Default to paper trading

    # Risk Controls
    position_multiplier: float = 1.0  # 0.5x - 2.0x
    min_confidence: float = 0.7  # 0.0 - 1.0
    max_leverage: int = 5  # 1 - 20

    # Token Filtering
    token_whitelist: List[str] = None  # None = all tokens allowed
    token_blacklist: List[str] = None  # Exclude specific tokens

    # Metadata
    priority: int = 1  # 1 = highest priority
    created_at: str = None
    updated_at: str = None

    # Performance tracking (populated from history)
    total_signals: int = 0
    signals_copied: int = 0
    win_count: int = 0
    total_pnl: float = 0.0

    def __post_init__(self):
        """Initialize timestamps and defaults"""
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = datetime.now().isoformat()
        if self.token_whitelist is None:
            self.token_whitelist = []
        if self.token_blacklist is None:
            self.token_blacklist = []

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'TraderConfig':
        """Create from dictionary"""
        return cls(**data)

    def allows_token(self, symbol: str) -> bool:
        """Check if this trader is allowed to trade this token"""
        # If blacklist exists and token is in it, reject
        if self.token_blacklist and symbol in self.token_blacklist:
            return False

        # If whitelist exists and token not in it, reject
        if self.token_whitelist and symbol not in self.token_whitelist:
            return False

        # Otherwise allow
        return True

    def update_timestamp(self):
        """Update the updated_at timestamp"""
        self.updated_at = datetime.now().isoformat()

    def calculate_position_size(self, base_size: float) -> float:
        """Calculate adjusted position size"""
        return base_size * self.position_multiplier

    def get_win_rate(self) -> float:
        """Calculate win rate"""
        if self.signals_copied == 0:
            return 0.0
        return self.win_count / self.signals_copied


class TraderManager:
    """Manages all trader configurations"""

    def __init__(self, config_file: str = 'traders_config.json'):
        self.config_file = Path(config_file)
        self.traders: Dict[str, TraderConfig] = {}
        self.load()

    def load(self):
        """Load trader configurations from file"""
        if not self.config_file.exists():
            logger.info(f"No trader config file found at {self.config_file}, creating new")
            self.save()
            return

        try:
            with open(self.config_file, 'r') as f:
                data = json.load(f)

            for trader_data in data.get('traders', []):
                trader = TraderConfig.from_dict(trader_data)
                self.traders[trader.id] = trader

            logger.info(f"Loaded {len(self.traders)} traders from config")

        except Exception as e:
            logger.error(f"Error loading trader config: {e}")
            self.traders = {}

    def save(self):
        """Save trader configurations to file"""
        try:
            data = {
                'traders': [trader.to_dict() for trader in self.traders.values()],
                'last_updated': datetime.now().isoformat()
            }

            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)

            logger.info(f"Saved {len(self.traders)} traders to config")

        except Exception as e:
            logger.error(f"Error saving trader config: {e}")

    def add_trader(self, trader: TraderConfig) -> bool:
        """Add a new trader"""
        if trader.id in self.traders:
            logger.warning(f"Trader {trader.id} already exists")
            return False

        self.traders[trader.id] = trader
        self.save()
        logger.info(f"Added trader: {trader.name}")
        return True

    def update_trader(self, trader_id: str, updates: Dict) -> bool:
        """Update trader configuration"""
        if trader_id not in self.traders:
            logger.warning(f"Trader {trader_id} not found")
            return False

        trader = self.traders[trader_id]

        # Update fields
        for key, value in updates.items():
            if hasattr(trader, key):
                setattr(trader, key, value)

        trader.update_timestamp()
        self.save()
        logger.info(f"Updated trader: {trader.name}")
        return True

    def remove_trader(self, trader_id: str) -> bool:
        """Remove a trader"""
        if trader_id not in self.traders:
            logger.warning(f"Trader {trader_id} not found")
            return False

        trader = self.traders.pop(trader_id)
        self.save()
        logger.info(f"Removed trader: {trader.name}")
        return True

    def get_trader(self, trader_id: str) -> Optional[TraderConfig]:
        """Get a specific trader"""
        return self.traders.get(trader_id)

    def get_active_traders(self) -> List[TraderConfig]:
        """Get all active traders"""
        return [t for t in self.traders.values() if t.active]

    def get_all_traders(self) -> List[TraderConfig]:
        """Get all traders"""
        return list(self.traders.values())

    def toggle_trader(self, trader_id: str) -> bool:
        """Toggle trader active status"""
        if trader_id not in self.traders:
            return False

        trader = self.traders[trader_id]
        trader.active = not trader.active
        trader.update_timestamp()
        self.save()

        status = "activated" if trader.active else "deactivated"
        logger.info(f"Trader {trader.name} {status}")
        return True

    def filter_signal(self, trader_id: str, symbol: str, confidence: float,
                     leverage: int = 1) -> tuple[bool, str]:
        """
        Check if a signal from this trader should be executed
        Returns: (allowed: bool, reason: str)
        """
        trader = self.get_trader(trader_id)
        if not trader:
            return False, "Trader not found"

        if not trader.active:
            return False, "Trader is inactive"

        # Check token filter
        if not trader.allows_token(symbol):
            return False, f"Token {symbol} not allowed for this trader"

        # Check confidence threshold
        if confidence < trader.min_confidence:
            return False, f"Confidence {confidence:.2f} below threshold {trader.min_confidence:.2f}"

        # Check leverage limit
        if leverage > trader.max_leverage:
            return False, f"Leverage {leverage}x exceeds limit {trader.max_leverage}x"

        return True, "Signal allowed"

    def record_signal(self, trader_id: str, copied: bool = True, won: bool = False,
                     pnl: float = 0.0):
        """Record signal performance"""
        trader = self.get_trader(trader_id)
        if not trader:
            return

        trader.total_signals += 1
        if copied:
            trader.signals_copied += 1
            if won:
                trader.win_count += 1
            trader.total_pnl += pnl

        self.save()


# Singleton instance
_trader_manager = None

def get_trader_manager(config_file: str = None) -> TraderManager:
    """Get or create trader manager singleton"""
    global _trader_manager
    if _trader_manager is None:
        if config_file is None:
            config_file = 'traders_config.json'
        _trader_manager = TraderManager(config_file)
    return _trader_manager


# Example usage
if __name__ == "__main__":
    # Create trader manager
    manager = TraderManager('test_traders.json')

    # Add some traders
    yun_qiang = TraderConfig(
        id='yun_qiang',
        name='Yun Qiang',
        source='binance',
        active=True,
        position_multiplier=1.0,
        min_confidence=0.7,
        max_leverage=10,
        token_whitelist=['BTC/USDT', 'ETH/USDT'],
        priority=1
    )

    crypto_loby = TraderConfig(
        id='crypto_loby',
        name='Crypto Loby',
        source='telegram',
        active=True,
        position_multiplier=0.8,
        min_confidence=0.75,
        max_leverage=5,
        token_blacklist=['DOGE/USDT', 'SHIB/USDT'],
        priority=2
    )

    manager.add_trader(yun_qiang)
    manager.add_trader(crypto_loby)

    # Test filtering
    allowed, reason = manager.filter_signal('yun_qiang', 'BTC/USDT', 0.85, 5)
    print(f"Signal allowed: {allowed} - {reason}")

    allowed, reason = manager.filter_signal('yun_qiang', 'ADA/USDT', 0.85, 5)
    print(f"Signal allowed: {allowed} - {reason}")

    # Print traders
    print("\nActive traders:")
    for trader in manager.get_active_traders():
        print(f"- {trader.name} ({trader.source}) - {trader.position_multiplier}x multiplier")
