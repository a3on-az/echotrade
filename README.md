# EchoTrade - Crypto Copy Trading Bot

**EchoTradeBot** is a sophisticated crypto copy trading bot that mirrors high-ROI Binance traders with comprehensive risk management. The bot focuses on profitability by copying traders like Yun Qiang (+1700% 30d ROI) with proper position sizing, stop losses, and drawdown protection.

## 🎯 Key Features

- **High-ROI Trader Mirroring**: Copy top-performing traders like Yun Qiang, Crypto Loby
- **Advanced Risk Management**: 2% position sizing, 2% stop-loss, <30% max drawdown
- **Multiple Trading Pairs**: BTC/USDT, ETH/USDT, BNB/USDT, ADA/USDT
- **Paper Trading Mode**: Test strategies safely before going live
- **Comprehensive Logging**: Detailed trade logs and performance tracking
- **Docker Support**: Easy containerized deployment
- **CLI Interface**: Full command-line control with status monitoring

## 🏗️ Architecture

```
EchoTrade/
├── main.py              # Main orchestration and CLI
├── config.py            # Configuration management
├── signals.py           # Signal fetching and simulation
├── risk.py              # Risk management and position sizing
├── execution.py         # Order execution with retry logic
├── logger.py            # Centralized logging
├── tests/               # Comprehensive test suite
│   ├── test_config.py
│   ├── test_signals.py
│   ├── test_risk.py     # Includes test_risk_caps_loss
│   └── test_execution.py
├── requirements.txt     # Python dependencies
├── Dockerfile          # Container setup
├── docker-compose.yml  # Multi-service deployment
└── .env.example        # Configuration template
```

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd EchoTrade

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy the environment template
cp .env.example .env

# Edit configuration (required for live trading)
nano .env
```

Key configuration parameters:
- `BINANCE_API_KEY` & `BINANCE_API_SECRET`: Your Binance API credentials
- `PORTFOLIO_VALUE`: Starting portfolio value (default: $10,000)
- `POSITION_SIZE_PERCENT`: Position size as % of portfolio (default: 2%)
- `STOP_LOSS_PERCENT`: Stop loss percentage (default: 2%)
- `MAX_DRAWDOWN_PERCENT`: Maximum drawdown limit (default: 30%)

### 3. Paper Trading (Recommended First)

```bash
# Run in paper trading mode
python main.py --paper

# Run with debug logging
python main.py --paper --log-level DEBUG

# Run for limited iterations (testing)
python main.py --paper --max-iterations 10

# Check current status
python main.py --status
```

### 4. Live Trading

```bash
# Run live trading (requires valid API keys)
python main.py

# Run in sandbox mode
SANDBOX_MODE=true python main.py
```

## 🐋 Docker Deployment

### Basic Docker Run

```bash
# Build the image
docker build -t echotrade .

# Run in paper mode
docker run -d --name echotrade-bot \
  --env-file .env \
  -v $(pwd)/logs:/app/logs \
  echotrade python main.py --paper
```

### Docker Compose (Recommended)

```bash
# Start the bot
docker-compose up -d

# View logs
docker-compose logs -f echotrade

# Stop the bot
docker-compose down

# Start with monitoring (optional)
docker-compose --profile monitoring up -d

# Start with log aggregation (optional)
docker-compose --profile logging up -d
```

## 📊 Trading Strategy

### Target Traders
- **Yun Qiang**: +1700% 30-day ROI, Priority 1
- **Crypto Loby**: +850% 30-day ROI, Priority 2

### Risk Management Rules
- **Position Sizing**: 2% of portfolio per trade
- **Stop Loss**: 2% below entry for long positions
- **Max Drawdown**: 30% portfolio drawdown limit
- **Concurrent Positions**: Maximum 5 positions
- **Minimum Trade**: $10 USDT minimum

### Signal Processing
1. **Market Data Analysis**: Real-time price and volatility monitoring
2. **Signal Generation**: Simulate high-ROI trader behavior
3. **Signal Strength**: Aggregate signals by confidence and sentiment
4. **Risk Validation**: Comprehensive pre-trade risk checks
5. **Order Execution**: Market orders with stop-loss protection

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/test_risk.py::TestRiskManager::test_risk_caps_loss
pytest tests/test_signals.py -v
pytest tests/test_execution.py -k paper_trading

# Run with coverage
pytest --cov=. --cov-report=html
```

Key test coverage:
- ✅ **test_risk_caps_loss**: Validates 30% drawdown limit enforcement
- ✅ Risk management and position sizing
- ✅ Signal generation and strength analysis  
- ✅ Order execution with retry logic
- ✅ Paper trading simulation

## 📈 Monitoring & Logging

### Log Files
- `logs/echotrade.log`: Main application logs
- `logs/trades.log`: Trade-specific events
- Console output with configurable levels

### Status Monitoring
```bash
# Real-time status
python main.py --status

# Docker logs
docker-compose logs -f echotrade

# Trade events
tail -f logs/echotrade.log | grep "POSITION_"
```

### Key Metrics
- Portfolio value and daily P&L
- Open positions and current drawdown
- Trade success rate and performance
- Risk limit adherence

## 🔧 Configuration Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `PORTFOLIO_VALUE` | 10000 | Initial portfolio value (USDT) |
| `POSITION_SIZE_PERCENT` | 2.0 | Position size as % of portfolio |
| `STOP_LOSS_PERCENT` | 2.0 | Stop loss percentage |
| `MAX_DRAWDOWN_PERCENT` | 30.0 | Maximum drawdown limit |
| `MIN_TRADE_AMOUNT` | 10.0 | Minimum trade size (USDT) |
| `MAX_CONCURRENT_POSITIONS` | 5 | Maximum open positions |
| `SIGNAL_CHECK_INTERVAL` | 60 | Signal check frequency (seconds) |
| `SANDBOX_MODE` | true | Use Binance testnet |

## 🔐 Security Best Practices

1. **API Key Security**:
   - Use Binance testnet for development
   - Restrict API permissions (trading only, no withdrawal)
   - Store keys in environment variables, never in code

2. **Container Security**:
   - Runs as non-root user
   - Minimal base image (python:3.12-slim)
   - Read-only configuration mounts

3. **Risk Management**:
   - Start with paper trading
   - Use small portfolio values initially
   - Monitor drawdown limits closely

## 🚨 Important Warnings

⚠️ **TRADING RISKS**: Cryptocurrency trading involves substantial risk of loss. This bot is for educational and research purposes.

⚠️ **PAPER TRADING FIRST**: Always test thoroughly in paper trading mode before risking real funds.

⚠️ **API SECURITY**: Never share your API keys. Use testnet for development.

⚠️ **POSITION SIZING**: Start with small position sizes and gradually increase as you gain confidence.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests (`pytest`)
4. Commit changes (`git commit -m 'Add amazing feature'`)
5. Push to branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

- Create an issue for bug reports
- Join our Discord for community support
- Check the wiki for advanced configuration

---

**Disclaimer**: This software is for educational purposes only. Trading cryptocurrencies carries significant financial risk. The authors are not responsible for any financial losses incurred through the use of this software.