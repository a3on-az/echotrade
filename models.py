"""
Database models for EchoTrade data persistence
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import json

Base = declarative_base()

class Trader(Base):
    """Model for target traders we're copying"""
    __tablename__ = 'traders'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    roi_30d = Column(Float, nullable=False)
    priority = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    signals = relationship("TradingSignalDB", back_populates="trader")

class TradingSignalDB(Base):
    """Model for trading signals"""
    __tablename__ = 'trading_signals'
    
    id = Column(Integer, primary_key=True)
    trader_id = Column(Integer, ForeignKey('traders.id'), nullable=False)
    symbol = Column(String(20), nullable=False)
    side = Column(String(10), nullable=False)  # 'buy' or 'sell'
    price = Column(Float, nullable=False)
    amount = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    processed = Column(Boolean, default=False)
    
    # Relationships
    trader = relationship("Trader", back_populates="signals")
    trades = relationship("Trade", back_populates="signal")

class Trade(Base):
    """Model for executed trades"""
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True)
    signal_id = Column(Integer, ForeignKey('trading_signals.id'), nullable=True)
    symbol = Column(String(20), nullable=False)
    side = Column(String(10), nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    quantity = Column(Float, nullable=False)
    stop_loss_price = Column(Float, nullable=True)
    
    # Trade status
    status = Column(String(20), default='open')  # open, closed, cancelled
    trade_type = Column(String(20), default='market')  # market, limit, stop
    
    # Timing
    entry_time = Column(DateTime, default=datetime.utcnow)
    exit_time = Column(DateTime, nullable=True)
    
    # Performance
    pnl = Column(Float, default=0.0)
    pnl_percentage = Column(Float, default=0.0)
    fees = Column(Float, default=0.0)
    
    # External references
    exchange_order_id = Column(String(100), nullable=True)
    
    # Relationships
    signal = relationship("TradingSignalDB", back_populates="trades")

class Portfolio(Base):
    """Model for portfolio snapshots"""
    __tablename__ = 'portfolio_snapshots'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    total_value = Column(Float, nullable=False)
    cash_balance = Column(Float, nullable=False)
    unrealized_pnl = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    daily_pnl = Column(Float, default=0.0)
    drawdown_current = Column(Float, default=0.0)
    drawdown_max = Column(Float, default=0.0)
    open_positions_count = Column(Integer, default=0)
    trades_today = Column(Integer, default=0)

class Position(Base):
    """Model for current open positions"""
    __tablename__ = 'positions'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False)
    side = Column(String(10), nullable=False)
    quantity = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    stop_loss_price = Column(Float, nullable=True)
    unrealized_pnl = Column(Float, default=0.0)
    entry_time = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class RiskMetrics(Base):
    """Model for risk metrics tracking"""
    __tablename__ = 'risk_metrics'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    portfolio_value = Column(Float, nullable=False)
    var_1d = Column(Float, nullable=True)  # Value at Risk 1 day
    var_7d = Column(Float, nullable=True)  # Value at Risk 7 days
    sharpe_ratio = Column(Float, nullable=True)
    sortino_ratio = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=False)
    volatility = Column(Float, nullable=True)
    beta = Column(Float, nullable=True)  # Beta vs BTC
    correlation_btc = Column(Float, nullable=True)

class SystemLog(Base):
    """Model for system logs and events"""
    __tablename__ = 'system_logs'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    level = Column(String(10), nullable=False)  # INFO, WARNING, ERROR, CRITICAL
    module = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    details = Column(Text, nullable=True)  # JSON string for additional data

class DatabaseManager:
    """Database connection and session management"""
    
    def __init__(self, database_url: str = "sqlite:///echotrade.db"):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def create_tables(self):
        """Create all tables"""
        Base.metadata.create_all(bind=self.engine)
        
    def get_session(self):
        """Get database session"""
        return self.SessionLocal()
        
    def init_default_traders(self):
        """Initialize default traders"""
        session = self.get_session()
        try:
            # Check if traders already exist
            if session.query(Trader).count() == 0:
                traders = [
                    Trader(name="Yun Qiang", roi_30d=1700.0, priority=1),
                    Trader(name="Crypto Loby", roi_30d=850.0, priority=2),
                ]
                session.add_all(traders)
                session.commit()
        finally:
            session.close()

# Database instance
db_manager = DatabaseManager()