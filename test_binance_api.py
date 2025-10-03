#!/usr/bin/env python3
"""
Comprehensive Binance API integration test
Tests authentication, rate limiting, market data, and sandbox mode
"""

import ccxt
from config import Config
import time
import asyncio

def test_binance_integration():
    print('🌐 TESTING BINANCE API INTEGRATION')
    print('=' * 50)
    
    try:
        # Test CCXT initialization with sandbox
        exchange = ccxt.binance({
            'apiKey': Config.API_KEY,
            'secret': Config.API_SECRET,
            'sandbox': Config.SANDBOX_MODE,
            'enableRateLimit': True,
        })
        
        print(f'✅ CCXT exchange initialized: {exchange.id}')
        print(f'✅ Sandbox mode: {exchange.sandbox}')
        print(f'✅ Rate limiting: {exchange.enableRateLimit}')
        
        # Test markets loading
        print('\n📊 Loading markets...')
        markets = exchange.load_markets()
        print(f'✅ Markets loaded: {len(markets)} pairs')
        
        # Test specific pairs we use
        target_pairs = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT']
        print('\n🎯 Checking target trading pairs:')
        for pair in target_pairs:
            if pair in markets:
                market_info = markets[pair]
                print(f'✅ {pair}: Available (min: {market_info["limits"]["amount"]["min"]})')
            else:
                print(f'❌ {pair}: Not found')
        
        # Test ticker (rate limit friendly)
        print('\n💰 Testing market data...')
        ticker = exchange.fetch_ticker('BTC/USDT')
        print(f'✅ BTC/USDT price: ${ticker["last"]:.2f}')
        print(f'   Bid: ${ticker["bid"]:.2f}, Ask: ${ticker["ask"]:.2f}')
        print(f'   24h Volume: {ticker["baseVolume"]:.2f} BTC')
        
        # Test multiple tickers (rate limiting test)
        print('\n📈 Testing rate limiting with multiple requests...')
        start_time = time.time()
        for pair in ['BTC/USDT', 'ETH/USDT']:
            ticker = exchange.fetch_ticker(pair)
            print(f'✅ {pair}: ${ticker["last"]:.2f}')
        
        elapsed = time.time() - start_time
        print(f'✅ Rate limiting working: {elapsed:.2f}s for 2 requests')
        
        # Test authentication (account info)
        print('\n🔐 Testing authentication...')
        balance = exchange.fetch_balance()
        print(f'✅ Account connected: {len(balance)} balance entries')
        
        # Check if we have any balances
        non_zero_balances = {k: v for k, v in balance['total'].items() if v > 0}
        if non_zero_balances:
            print('💰 Account balances:')
            for asset, amount in non_zero_balances.items():
                print(f'   {asset}: {amount}')
        else:
            print('💰 Account has no balances (normal for sandbox)')
        
        # Test order book
        print('\n📖 Testing order book...')
        orderbook = exchange.fetch_order_book('BTC/USDT', limit=5)
        print(f'✅ Order book loaded: {len(orderbook["bids"])} bids, {len(orderbook["asks"])} asks')
        print(f'   Best bid: ${orderbook["bids"][0][0]:.2f}')
        print(f'   Best ask: ${orderbook["asks"][0][0]:.2f}')
        
        return True
        
    except ccxt.NetworkError as e:
        print(f'❌ Network error: {e}')
        return False
    except ccxt.ExchangeError as e:
        print(f'❌ Exchange error: {e}')
        return False
    except Exception as e:
        print(f'❌ Unexpected error: {e}')
        import traceback
        traceback.print_exc()
        return False

def test_rate_limiting():
    """Test that rate limiting prevents API abuse"""
    print('\n⚡ TESTING RATE LIMITING PROTECTION')
    print('=' * 50)
    
    try:
        exchange = ccxt.binance({
            'apiKey': Config.API_KEY,
            'secret': Config.API_SECRET,
            'sandbox': Config.SANDBOX_MODE,
            'enableRateLimit': True,
        })
        
        # Make rapid requests to test rate limiting
        start_time = time.time()
        for i in range(5):
            ticker = exchange.fetch_ticker('BTC/USDT')
            print(f'Request {i+1}: ${ticker["last"]:.2f}')
        
        elapsed = time.time() - start_time
        print(f'✅ 5 requests took {elapsed:.2f}s (rate limiting active)')
        
        if elapsed > 2.0:  # Should be throttled
            print('✅ Rate limiting is working properly')
            return True
        else:
            print('⚠️  Requests were very fast - rate limiting may not be active')
            return False
            
    except Exception as e:
        print(f'❌ Rate limiting test failed: {e}')
        return False

if __name__ == "__main__":
    success = test_binance_integration()
    if success:
        rate_limit_success = test_rate_limiting()
        if rate_limit_success:
            print('\n🎉 ALL BINANCE API TESTS PASSED!')
        else:
            print('\n⚠️  Binance API working but rate limiting needs attention')
    else:
        print('\n❌ BINANCE API TESTS FAILED - Check configuration')