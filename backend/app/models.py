import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class LogLevel(str, enum.Enum):
    success = "success"
    error = "error"
    info = "info"
    warning = "warning"


class OrderSide(str, enum.Enum):
    buy = "buy"
    sell = "sell"


class OrderStatus(str, enum.Enum):
    filled = "filled"
    cancelled = "cancelled"
    pending = "pending"


class StrategyConfig(Base):
    __tablename__ = "strategy_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset: Mapped[str] = mapped_column(String(20), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    ma_short_period: Mapped[int] = mapped_column(Integer, nullable=False)
    ma_long_period: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BotStatus(Base):
    __tablename__ = "bot_status"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status: Mapped[str] = mapped_column(String(20), default="Running")
    daily_pnl: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    current_asset: Mapped[str] = mapped_column(String(20), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MarketTick(Base):
    __tablename__ = "market_ticks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset: Mapped[str] = mapped_column(String(20), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)
    volume: Mapped[float] = mapped_column(Numeric(20, 4), default=0)
    tick_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BacktestResult(Base):
    __tablename__ = "backtest_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_config_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("strategy_configs.id"), nullable=True
    )
    period_label: Mapped[str] = mapped_column(String(20), default="6 Months")
    total_return: Mapped[float] = mapped_column(Float, default=0)
    win_rate: Mapped[float] = mapped_column(Float, default=0)
    max_drawdown: Mapped[float] = mapped_column(Float, default=0)
    sharpe_ratio: Mapped[float] = mapped_column(Float, default=0)
    equity_curve: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LogEntry(Base):
    __tablename__ = "logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    level: Mapped[LogLevel] = mapped_column(Enum(LogLevel), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AppSettings(Base):
    __tablename__ = "app_settings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    api_key_masked: Mapped[str | None] = mapped_column(String(255), nullable=True)
    api_secret_masked: Mapped[str | None] = mapped_column(String(255), nullable=True)
    paper_trading: Mapped[bool] = mapped_column(Boolean, default=True)
    dark_mode: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PaperAccount(Base):
    __tablename__ = "paper_account"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    balance: Mapped[float] = mapped_column(Numeric(14, 2), default=10000)
    open_position_asset: Mapped[str | None] = mapped_column(String(20), nullable=True)
    open_position_qty: Mapped[float] = mapped_column(Numeric(14, 4), default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PaperOrder(Base):
    __tablename__ = "paper_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    side: Mapped[OrderSide] = mapped_column(Enum(OrderSide), nullable=False)
    asset: Mapped[str] = mapped_column(String(20), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.filled)
    simulated: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
