"""
FastAPI web server for EchoTrade frontend integration
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import json
import asyncio
from datetime import datetime, timedelta
import uvicorn

from models import (
    db_manager, Trader, Trade, Portfolio, Position, RiskMetrics, SystemLog
)
from config import Config
from main import EchoTradeBot

app = FastAPI(title="EchoTrade API", version="1.0.0")

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global bot instance
bot_instance = None
websocket_connections = []

# Dependency to get database session
def get_db():
    db = db_manager.get_session()
    try:
        yield db
    finally:
        db.close()

class ConnectionManager:
    """WebSocket connection manager"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove dead connections
                self.active_connections.remove(connection)

manager = ConnectionManager()

@app.on_event("startup")
async def startup_event():
    """Initialize database and bot on startup"""
    db_manager.create_tables()
    db_manager.init_default_traders()

# === PORTFOLIO ENDPOINTS ===

@app.get("/api/portfolio/status")
async def get_portfolio_status(db: Session = Depends(get_db)):
    """Get current portfolio status"""
    global bot_instance
    
    if bot_instance:
        # Get live data from bot
        risk_summary = bot_instance.risk_manager.get_risk_summary()
        return {
            "portfolio_value": risk_summary['portfolio_value'],
            "daily_pnl": risk_summary['daily_pnl'],
            "open_positions": risk_summary['open_positions'],
            "current_drawdown": risk_summary['current_drawdown'],
            "max_drawdown": risk_summary['max_drawdown'],
            "trades_today": risk_summary['trades_today'],
            "position_details": risk_summary['position_details'],
            "is_running": bot_instance.running,
            "paper_trading": bot_instance.paper_trading
        }
    else:
        # Get from database
        latest_portfolio = db.query(Portfolio).order_by(Portfolio.timestamp.desc()).first()
        if latest_portfolio:
            return {
                "portfolio_value": latest_portfolio.total_value,
                "daily_pnl": latest_portfolio.daily_pnl,
                "open_positions": latest_portfolio.open_positions_count,
                "current_drawdown": latest_portfolio.drawdown_current,
                "max_drawdown": latest_portfolio.drawdown_max,
                "trades_today": latest_portfolio.trades_today,
                "position_details": {},
                "is_running": False,
                "paper_trading": True
            }
        else:
            return {
                "portfolio_value": Config.PORTFOLIO_VALUE,
                "daily_pnl": 0.0,
                "open_positions": 0,
                "current_drawdown": 0.0,
                "max_drawdown": 0.0,
                "trades_today": 0,
                "position_details": {},
                "is_running": False,
                "paper_trading": True
            }

@app.get("/api/portfolio/history")
async def get_portfolio_history(days: int = 30, db: Session = Depends(get_db)):
    """Get portfolio performance history"""
    start_date = datetime.utcnow() - timedelta(days=days)
    snapshots = db.query(Portfolio).filter(
        Portfolio.timestamp >= start_date
    ).order_by(Portfolio.timestamp.asc()).all()
    
    return [
        {
            "timestamp": snapshot.timestamp.isoformat(),
            "total_value": snapshot.total_value,
            "daily_pnl": snapshot.daily_pnl,
            "drawdown": snapshot.drawdown_current,
            "open_positions": snapshot.open_positions_count
        }
        for snapshot in snapshots
    ]

# === TRADING ENDPOINTS ===

@app.get("/api/trades/recent")
async def get_recent_trades(limit: int = 50, db: Session = Depends(get_db)):
    """Get recent trades"""
    trades = db.query(Trade).order_by(Trade.entry_time.desc()).limit(limit).all()
    
    return [
        {
            "id": trade.id,
            "symbol": trade.symbol,
            "side": trade.side,
            "entry_price": trade.entry_price,
            "exit_price": trade.exit_price,
            "quantity": trade.quantity,
            "pnl": trade.pnl,
            "pnl_percentage": trade.pnl_percentage,
            "status": trade.status,
            "entry_time": trade.entry_time.isoformat(),
            "exit_time": trade.exit_time.isoformat() if trade.exit_time else None
        }
        for trade in trades
    ]

@app.get("/api/positions/current")
async def get_current_positions(db: Session = Depends(get_db)):
    """Get current open positions"""
    positions = db.query(Position).all()
    
    return [
        {
            "id": position.id,
            "symbol": position.symbol,
            "side": position.side,
            "quantity": position.quantity,
            "entry_price": position.entry_price,
            "current_price": position.current_price,
            "stop_loss_price": position.stop_loss_price,
            "unrealized_pnl": position.unrealized_pnl,
            "entry_time": position.entry_time.isoformat()
        }
        for position in positions
    ]

# === TRADER ENDPOINTS ===

@app.get("/api/traders")
async def get_traders(db: Session = Depends(get_db)):
    """Get all traders"""
    traders = db.query(Trader).order_by(Trader.priority).all()
    
    return [
        {
            "id": trader.id,
            "name": trader.name,
            "roi_30d": trader.roi_30d,
            "priority": trader.priority,
            "is_active": trader.is_active
        }
        for trader in traders
    ]

@app.put("/api/traders/{trader_id}")
async def update_trader(trader_id: int, trader_data: Dict[str, Any], db: Session = Depends(get_db)):
    """Update trader configuration"""
    trader = db.query(Trader).filter(Trader.id == trader_id).first()
    if not trader:
        raise HTTPException(status_code=404, detail="Trader not found")
    
    if "is_active" in trader_data:
        trader.is_active = trader_data["is_active"]
    if "priority" in trader_data:
        trader.priority = trader_data["priority"]
    
    trader.updated_at = datetime.utcnow()
    db.commit()
    
    return {"status": "updated"}

# === RISK ENDPOINTS ===

@app.get("/api/risk/metrics")
async def get_risk_metrics(days: int = 30, db: Session = Depends(get_db)):
    """Get risk metrics history"""
    start_date = datetime.utcnow() - timedelta(days=days)
    metrics = db.query(RiskMetrics).filter(
        RiskMetrics.timestamp >= start_date
    ).order_by(RiskMetrics.timestamp.desc()).limit(100).all()
    
    return [
        {
            "timestamp": metric.timestamp.isoformat(),
            "portfolio_value": metric.portfolio_value,
            "max_drawdown": metric.max_drawdown,
            "sharpe_ratio": metric.sharpe_ratio,
            "volatility": metric.volatility
        }
        for metric in metrics
    ]

# === BOT CONTROL ENDPOINTS ===

@app.post("/api/bot/start")
async def start_bot(paper_trading: bool = True):
    """Start the trading bot"""
    global bot_instance
    
    if bot_instance and bot_instance.running:
        raise HTTPException(status_code=400, detail="Bot is already running")
    
    try:
        bot_instance = EchoTradeBot(paper_trading=paper_trading)
        # Start bot in background task
        asyncio.create_task(run_bot_background())
        return {"status": "started", "paper_trading": paper_trading}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/bot/stop")
async def stop_bot():
    """Stop the trading bot"""
    global bot_instance
    
    if not bot_instance or not bot_instance.running:
        raise HTTPException(status_code=400, detail="Bot is not running")
    
    bot_instance.running = False
    return {"status": "stopped"}

@app.get("/api/bot/status")
async def get_bot_status():
    """Get bot status"""
    global bot_instance
    
    if bot_instance:
        return {
            "is_running": bot_instance.running,
            "paper_trading": bot_instance.paper_trading,
            "uptime": "N/A"  # Could track this
        }
    else:
        return {
            "is_running": False,
            "paper_trading": True,
            "uptime": "0"
        }

# === CONFIGURATION ENDPOINTS ===

@app.get("/api/config")
async def get_config():
    """Get current configuration"""
    return {
        "portfolio_value": Config.PORTFOLIO_VALUE,
        "position_size_percent": Config.POSITION_SIZE_PERCENT,
        "stop_loss_percent": Config.STOP_LOSS_PERCENT,
        "max_drawdown_percent": Config.MAX_DRAWDOWN_PERCENT,
        "trading_pairs": Config.TRADING_PAIRS,
        "target_traders": Config.TARGET_TRADERS
    }

@app.put("/api/config")
async def update_config(config_data: Dict[str, Any]):
    """Update configuration (runtime only, not persistent)"""
    # This would update runtime configuration
    # For production, implement proper configuration management
    return {"status": "updated", "message": "Configuration updated (runtime only)"}

# === WEBSOCKET ENDPOINTS ===

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and send updates
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

async def run_bot_background():
    """Run bot in background task"""
    global bot_instance
    
    if bot_instance:
        try:
            # This would run the bot's main loop
            # For now, just simulate
            while bot_instance.running:
                # Send periodic updates via WebSocket
                if manager.active_connections:
                    status_update = {
                        "type": "status_update",
                        "data": await get_portfolio_status()
                    }
                    await manager.broadcast(json.dumps(status_update))
                
                await asyncio.sleep(10)  # Update every 10 seconds
                
        except Exception as e:
            print(f"Bot error: {e}")
        finally:
            if bot_instance:
                bot_instance.running = False

# === LOGS ENDPOINT ===

@app.get("/api/logs")
async def get_logs(limit: int = 100, level: str = None, db: Session = Depends(get_db)):
    """Get system logs"""
    query = db.query(SystemLog)
    
    if level:
        query = query.filter(SystemLog.level == level.upper())
    
    logs = query.order_by(SystemLog.timestamp.desc()).limit(limit).all()
    
    return [
        {
            "id": log.id,
            "timestamp": log.timestamp.isoformat(),
            "level": log.level,
            "module": log.module,
            "message": log.message,
            "details": json.loads(log.details) if log.details else None
        }
        for log in logs
    ]

# === TRADER MANAGEMENT ENDPOINTS ===

from trader_config import get_trader_manager, TraderConfig

@app.get("/api/traders")
async def get_all_traders():
    """Get all configured traders"""
    manager = get_trader_manager()
    traders = manager.get_all_traders()
    return {
        "traders": [t.to_dict() for t in traders],
        "total": len(traders),
        "active": len([t for t in traders if t.active])
    }

@app.get("/api/traders/{trader_id}")
async def get_trader(trader_id: str):
    """Get specific trader details"""
    manager = get_trader_manager()
    trader = manager.get_trader(trader_id)

    if not trader:
        raise HTTPException(status_code=404, detail="Trader not found")

    return trader.to_dict()

@app.post("/api/traders")
async def add_trader(trader_data: Dict[str, Any]):
    """Add a new trader"""
    manager = get_trader_manager()

    try:
        # Create trader config
        trader = TraderConfig(
            id=trader_data.get('id'),
            name=trader_data.get('name'),
            source=trader_data.get('source', 'manual'),
            active=trader_data.get('active', True),
            paper_trade_only=trader_data.get('paper_trade_only', True),
            position_multiplier=trader_data.get('position_multiplier', 1.0),
            min_confidence=trader_data.get('min_confidence', 0.7),
            max_leverage=trader_data.get('max_leverage', 5),
            token_whitelist=trader_data.get('token_whitelist', []),
            token_blacklist=trader_data.get('token_blacklist', []),
            priority=trader_data.get('priority', 1)
        )

        success = manager.add_trader(trader)

        if not success:
            raise HTTPException(status_code=400, detail="Trader already exists")

        return {
            "success": True,
            "message": f"Trader {trader.name} added successfully",
            "trader": trader.to_dict()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/traders/{trader_id}")
async def update_trader(trader_id: str, updates: Dict[str, Any]):
    """Update trader configuration"""
    manager = get_trader_manager()

    success = manager.update_trader(trader_id, updates)

    if not success:
        raise HTTPException(status_code=404, detail="Trader not found")

    trader = manager.get_trader(trader_id)
    return {
        "success": True,
        "message": f"Trader {trader.name} updated successfully",
        "trader": trader.to_dict()
    }

@app.delete("/api/traders/{trader_id}")
async def delete_trader(trader_id: str):
    """Remove a trader"""
    manager = get_trader_manager()

    trader = manager.get_trader(trader_id)
    if not trader:
        raise HTTPException(status_code=404, detail="Trader not found")

    trader_name = trader.name
    success = manager.remove_trader(trader_id)

    return {
        "success": success,
        "message": f"Trader {trader_name} removed successfully"
    }

@app.post("/api/traders/{trader_id}/toggle")
async def toggle_trader(trader_id: str):
    """Toggle trader active status"""
    manager = get_trader_manager()

    success = manager.toggle_trader(trader_id)

    if not success:
        raise HTTPException(status_code=404, detail="Trader not found")

    trader = manager.get_trader(trader_id)
    status = "activated" if trader.active else "deactivated"

    return {
        "success": True,
        "message": f"Trader {trader.name} {status}",
        "active": trader.active
    }

@app.put("/api/traders/{trader_id}/multiplier")
async def update_multiplier(trader_id: str, data: Dict[str, float]):
    """Update position size multiplier"""
    manager = get_trader_manager()

    multiplier = data.get('multiplier', 1.0)

    # Validate range
    if not (0.1 <= multiplier <= 3.0):
        raise HTTPException(status_code=400, detail="Multiplier must be between 0.1 and 3.0")

    success = manager.update_trader(trader_id, {'position_multiplier': multiplier})

    if not success:
        raise HTTPException(status_code=404, detail="Trader not found")

    trader = manager.get_trader(trader_id)
    return {
        "success": True,
        "message": f"Position multiplier updated to {multiplier}x",
        "trader": trader.to_dict()
    }

@app.put("/api/traders/{trader_id}/tokens")
async def update_token_filter(trader_id: str, data: Dict[str, List[str]]):
    """Update token whitelist/blacklist"""
    manager = get_trader_manager()

    updates = {}
    if 'whitelist' in data:
        updates['token_whitelist'] = data['whitelist']
    if 'blacklist' in data:
        updates['token_blacklist'] = data['blacklist']

    success = manager.update_trader(trader_id, updates)

    if not success:
        raise HTTPException(status_code=404, detail="Trader not found")

    trader = manager.get_trader(trader_id)
    return {
        "success": True,
        "message": "Token filters updated successfully",
        "trader": trader.to_dict()
    }

@app.get("/api/traders/{trader_id}/metrics")
async def get_trader_metrics(trader_id: str):
    """Get trader performance metrics"""
    manager = get_trader_manager()
    trader = manager.get_trader(trader_id)

    if not trader:
        raise HTTPException(status_code=404, detail="Trader not found")

    # Calculate metrics
    win_rate = trader.get_win_rate()

    return {
        "trader_id": trader_id,
        "trader_name": trader.name,
        "total_signals": trader.total_signals,
        "signals_copied": trader.signals_copied,
        "win_count": trader.win_count,
        "win_rate": win_rate,
        "total_pnl": trader.total_pnl,
        "avg_pnl_per_trade": trader.total_pnl / trader.signals_copied if trader.signals_copied > 0 else 0,
        "active": trader.active,
        "paper_trade_only": trader.paper_trade_only
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)