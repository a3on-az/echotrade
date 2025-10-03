# Phase 4: Trader Sourcing & Tracking - Deployment Guide

## Overview
Phase 4 extends EchoTradeBot with ML-powered trader sourcing and ranking capabilities. This system independently tracks top crypto traders from public sources since Binance leaderboards are unreliable.

## Architecture
- **data_sourcing.py**: Scrapes trader data from Twitter, eToro, TradingView
- **ml_model.py**: Ranks traders using custom scoring algorithm + RandomForestRegressor
- **tracker.py**: Daily monitoring and Telegram alerts
- **integration.py**: API service for main bot integration
- **tests/**: Comprehensive test suite

## Quick Start

### 1. Local Development Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
python data_sourcing.py

# Run ML ranking
python ml_model.py

# Start tracker (daily monitoring)
python tracker.py --daily
```

### 2. Docker Deployment
```bash
# Build and run services
docker-compose up -d

# Check logs
docker-compose logs -f ml-service
```

### 3. Australian VPS Setup
```bash
# Navigate to terraform directory
cd terraform/

# Initialize Terraform
terraform init

# Review and apply infrastructure
terraform plan
terraform apply

# Connect to VPS
ssh -i your_ssh_key.pem ec2-user@$(terraform output -raw public_ip)
```

## Configuration

### Required API Keys
Create `.env` file with:
```bash
# Twitter API (optional - for enhanced scraping)
TWITTER_CONSUMER_KEY=your_key
TWITTER_CONSUMER_SECRET=your_secret
TWITTER_ACCESS_TOKEN=your_token
TWITTER_ACCESS_TOKEN_SECRET=your_token_secret

# Telegram Bot (for alerts)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Proxy settings (recommended for scraping)
HTTP_PROXY=http://your-proxy:port
HTTPS_PROXY=https://your-proxy:port
```

### Trader Scoring Algorithm
Default formula: `score = (ROI * 0.5) + (win_rate * 0.3) - (drawdown * 0.2)`

Customize in `ml_model.py`:
```python
def calculate_score(roi, win_rate, drawdown):
    return (roi * 0.5) + (win_rate * 0.3) - (drawdown * 0.2)
```

## Integration with Main Bot

### API Endpoints
- `GET /api/top_traders` - Returns top 5 ranked traders
- `GET /api/health` - Service health check

### Main Bot Integration
Add to your existing `main.py`:
```python
import requests

def get_ml_traders():
    try:
        response = requests.get('http://ml-service:8051/api/top_traders')
        if response.status_code == 200:
            return response.json()['traders']
    except Exception as e:
        print(f"ML service unavailable: {e}")
    return []
```

## Compliance & Ethics
- **No private data**: Only scrapes public profiles
- **Rate limiting**: Built-in delays to respect ToS
- **Australian jurisdiction**: VPS in Sydney region
- **GDPR compliant**: No personal data storage

## Monitoring & Alerts
- Daily performance scans
- Telegram notifications for significant changes
- Health check endpoints for uptime monitoring

## Performance Optimization
- **M6i.large instance**: 2 vCPU, 8GB RAM for ML processing
- **10Gbps bandwidth**: Fast scraping and data processing
- **SQLite database**: Lightweight, file-based storage
- **Docker containerization**: Scalable deployment

## Testing
```bash
# Run all tests
pytest tests/

# Test specific components
pytest tests/test_ml_model.py -v
pytest tests/test_data_sourcing.py -v
```

## Troubleshooting

### Common Issues
1. **Scraping blocked**: Rotate proxies, reduce request frequency
2. **ML model accuracy low**: Increase training data, tune hyperparameters
3. **Database locked**: Check for concurrent access, use WAL mode

### Logs Location
- Docker: `docker-compose logs ml-service`
- VPS: `/var/log/echotrade/`
- Local: `./logs/trader_sourcing.log`

## Next Steps
1. Deploy to Australian VPS using Terraform
2. Configure API keys and proxy settings  
3. Run initial data collection (`python data_sourcing.py`)
4. Monitor trader rankings and performance
5. Integrate with existing bot trading signals

## Support
- Check logs for detailed error messages
- Test API endpoints individually
- Validate database schema and data quality
- Monitor resource usage on VPS

Estimated implementation time: 1-2 days with M4 server setup.