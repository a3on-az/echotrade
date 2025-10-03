#!/usr/bin/env python3
"""
Initialize Default Traders
Sets up Yun Qiang and Crypto Loby from Config
"""

import logging
from trader_config import get_trader_manager, TraderConfig
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_default_traders():
    """Initialize default traders from Config.TARGET_TRADERS"""
    manager = get_trader_manager()

    # Check if already initialized
    existing = manager.get_all_traders()
    if len(existing) > 0:
        logger.info(f"Traders already configured: {[t.name for t in existing]}")
        return existing

    logger.info("Initializing default traders from Config...")

    traders_added = []

    for trader_data in Config.TARGET_TRADERS:
        # Create trader ID from name
        trader_id = trader_data['name'].lower().replace(' ', '_')

        trader = TraderConfig(
            id=trader_id,
            name=trader_data['name'],
            source='binance',
            active=True,
            paper_trade_only=True,  # Start in paper mode
            position_multiplier=1.0,
            min_confidence=0.7,
            max_leverage=10,
            priority=trader_data.get('priority', 1),
            token_whitelist=[],  # Allow all tokens by default
            token_blacklist=[]
        )

        success = manager.add_trader(trader)
        if success:
            traders_added.append(trader.name)
            logger.info(f"✅ Added trader: {trader.name}")
        else:
            logger.warning(f"⚠️  Trader {trader.name} already exists")

    logger.info(f"✅ Initialization complete! Added {len(traders_added)} traders")
    return manager.get_all_traders()

def reset_traders():
    """Remove all traders and reinitialize"""
    manager = get_trader_manager()

    traders = manager.get_all_traders()
    for trader in traders:
        manager.remove_trader(trader.id)
        logger.info(f"Removed trader: {trader.name}")

    logger.info("All traders removed. Reinitializing...")
    return init_default_traders()

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--reset':
        print("🔄 Resetting all traders...")
        traders = reset_traders()
    else:
        print("🚀 Initializing default traders...")
        traders = init_default_traders()

    print("\n📊 Current Traders:")
    for trader in traders:
        status = "🟢 Active" if trader.active else "🔴 Inactive"
        mode = "📝 Paper" if trader.paper_trade_only else "💰 Live"
        print(f"  {status} {mode} - {trader.name} ({trader.source}) - {trader.position_multiplier}x")

    print(f"\n✅ Total: {len(traders)} traders configured")
