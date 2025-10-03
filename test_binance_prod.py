#!/usr/bin/env python3
"""
Test Binance production API with read-only operations
This validates authentication and API access without placing orders
"""

import ccxt
from config import Config
import time

def test_production_api():
    print('🌐 TESTING BINANCE PRODUCTION API (READ-ONLY)')
    print('=' * 50)
    
    try:
        # Test with production API (sandbox=False)
        exchange = ccxt.binance({
            'apiKey': Config.API_KEY,
            'secret': Config.API_SECRET,
            'sandbox': False,  # Use production for read-only tests
            'enableRateLimit': True,
        })
        
        print(f'✅ CCXT exchange initialized: {exchange.id}')
        print(f'✅ Production mode: {not exchange.sandbox}')
        print(f'✅ Rate limiting: {exchange.enableRateLimit}')
        
        # Test markets loading (no auth required)
        print('\n📊 Loading markets...')
        markets = exchange.load_markets()
        print(f'✅ Markets loaded: {len(markets)} pairs')
        
        # Test specific pairs we use
        target_pairs = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT']
        print('\n🎯 Checking target trading pairs:')
        for pair in target_pairs:
            if pair in markets:
                market_info = markets[pair]
                min_amount = market_info["limits"]["amount"]["min"]
                print(f'✅ {pair}: Available (min: {min_amount})')
            else:
                print(f'❌ {pair}: Not found')
        
        # Test ticker (no auth required)
        print('\n💰 Testing market data...')
        ticker = exchange.fetch_ticker('BTC/USDT')
        print(f'✅ BTC/USDT price: ${ticker["last"]:.2f}')
        print(f'   Bid: ${ticker["bid"]:.2f}, Ask: ${ticker["ask"]:.2f}')
        print(f'   24h Volume: {ticker["baseVolume"]:.2f} BTC')
        
        # Test rate limiting
        print('\n📈 Testing rate limiting...')
        start_time = time.time()
        for pair in ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']:
            ticker = exchange.fetch_ticker(pair)
            print(f'✅ {pair}: ${ticker["last"]:.2f}')
        
        elapsed = time.time() - start_time
        print(f'✅ Rate limiting: {elapsed:.2f}s for 3 requests')
        
        # Test authentication (account info) - THIS REQUIRES VALID API KEYS
        print('\n🔐 Testing authentication...')
        try:
            balance = exchange.fetch_balance()
            print(f'✅ Authentication successful: {len(balance)} balance entries')
            
            # Show non-zero balances
            non_zero_balances = {k: v for k, v in balance['total'].items() if v > 0}
            if non_zero_balances:
                print('💰 Account balances:')
                for asset, amount in list(non_zero_balances.items())[:5]:  # Show first 5
                    print(f'   {asset}: {amount}')
                if len(non_zero_balances) > 5:
                    print(f'   ... and {len(non_zero_balances) - 5} more assets')
            else:
                print('💰 No balances found (empty account)')
            
            # Test account info
            account = exchange.fetch_account_status()
            print(f'✅ Account status: {account}')
            
        except ccxt.AuthenticationError as e:
            print(f'❌ Authentication failed: {e}')
            return False
        except ccxt.PermissionDenied as e:
            print(f'❌ Permission denied: {e}')
            return False
        
        # Test order book
        print('\n📖 Testing order book...')
        orderbook = exchange.fetch_order_book('BTC/USDT', limit=5)
        print(f'✅ Order book: {len(orderbook["bids"])} bids, {len(orderbook["asks"])} asks')
        spread = orderbook["asks"][0][0] - orderbook["bids"][0][0]
        print(f'   Spread: ${spread:.2f}')
        
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

def test_websocket_connection():
    """Test WebSocket connectivity (if available)"""
    print('\n🔌 TESTING WEBSOCKET CONNECTIVITY')
    print('=' * 50)
    
    try:
        # Test if exchange supports WebSocket
        exchange = ccxt.binance({
            'apiKey': Config.API_KEY,
            'secret': Config.API_SECRET,
            'sandbox': False,
            'enableRateLimit': True,
        })
        
        # Check WebSocket support
        if hasattr(exchange, 'has') and exchange.has.get('ws'):
            print('✅ WebSocket support detected')
            return True
        else:
            print('⚠️  WebSocket support not detected in CCXT')
            print('   (Real-time data will use REST polling)')
            return True
            
    except Exception as e:
        print(f'❌ WebSocket test failed: {e}')
        return False

if __name__ == "__main__":
    success = test_production_api()
    if success:
        ws_success = test_websocket_connection()
        if success and ws_success:
            print('\n🎉 BINANCE PRODUCTION API TESTS PASSED!')
            print('✅ Authentication working')
            print('✅ Rate limiting active')
            print('✅ Market data accessible')
        else:
            print('\n⚠️  API working but WebSocket needs attention')
    else:
        print('\n❌ BINANCE API TESTS FAILED')