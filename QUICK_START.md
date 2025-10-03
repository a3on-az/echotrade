# 🚀 EchoTrade - Quick Start Guide

**For Hedge Fund Review & UX Testing**

---

## ⚡ Start Dashboard (Fastest Way)

```bash
cd ~/projects/echotrade
source venv/bin/activate
python app.py
```

Then open: **http://localhost:8050**

---

## 🎯 What You'll See

### Dashboard Pages

1. **Main Dashboard** (/)
   - Portfolio: $10,000 (simulated)
   - Daily P&L tracking
   - ROI metrics
   - 🛑 Emergency Stop button
   - Live equity curve

2. **Traders** (/traders)
   - Yun Qiang (+1,700% ROI)
   - Crypto Loby (+850% ROI)
   - Toggle traders on/off
   - Allocation pie chart

3. **Analytics** (/analytics)
   - Backtest results
   - Performance metrics
   - Historical charts

4. **Settings** (/settings)
   - API keys (masked)
   - Risk parameters
   - System controls

---

## 🔧 Start with PM2 (Production Style)

```bash
cd ~/projects/echotrade
pm2 start ecosystem.config.js
pm2 logs echotrade-dashboard
```

This starts:
- ✅ Trading bot (paper mode)
- ✅ Dashboard (port 8050)
- ✅ API server (port 8000)

---

## 📊 Current Configuration

**Mode:** Paper Trading (100% safe, no real money)
- Portfolio: $10,000 USDT (simulated)
- Position Size: 2% per trade ($200)
- Stop Loss: 2% below entry
- Max Drawdown: 30% limit

**API Keys:** Test keys configured
- Ready for Binance testnet
- Will switch to production when NZ corp ready

---

## 🎨 UI Features to Review

### Design
- ⚫ Dark mode (cyberpunk aesthetic)
- 📱 Mobile responsive
- 🎨 Professional color scheme
- 🔄 Real-time updates (5s refresh)

### Colors
- 🟢 Green: Success/profit
- 🟡 Yellow: Warnings
- 🔴 Red: Danger/losses
- 🔵 Blue: Primary actions

---

## ⚙️ PM2 Commands

```bash
pm2 list                    # Check all services
pm2 logs                    # View all logs
pm2 restart all             # Restart everything
pm2 stop all                # Stop all services
pm2 delete all              # Remove all services
```

---

## 📁 Key Files

```
~/projects/echotrade/
├── app.py                   # Dashboard (START HERE)
├── main.py                  # Trading bot
├── api_server.py            # REST API
├── .env                     # Configuration
├── ecosystem.config.js      # PM2 config
└── logs/                    # All logs
```

---

## 🐛 Troubleshooting

### Dashboard won't start
```bash
cd ~/projects/echotrade
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

### Check logs
```bash
tail -f ~/projects/echotrade/logs/echotrade.log
```

### Port already in use
```bash
lsof -ti:8050 | xargs kill -9
```

---

## 🔐 Security Notes

✅ **Currently in Paper Trading Mode**
- No real money at risk
- Safe for testing
- Full feature preview

⚠️ **Before Going Live:**
1. Get production Binance API keys
2. Update .env file
3. Set PAPER_TRADING=false
4. Start with small capital ($500-1000)

---

## 📞 Quick Reference

**Dashboard:** http://localhost:8050
**API:** http://localhost:8000
**Logs:** ~/projects/echotrade/logs/
**Config:** ~/projects/echotrade/.env

**Status:** READY FOR UX REVIEW ✅

---

**Next Step:** Open terminal and run:
```bash
cd ~/projects/echotrade && source venv/bin/activate && python app.py
```
