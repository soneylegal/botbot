from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TradeModeEnum(str, Enum):
    paper = "paper"
    live = "live"


class AuthRegisterIn(BaseModel):
    email: str
    password: str = Field(..., min_length=6)


class AuthLoginIn(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


class RefreshTokenIn(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: str
    email: str


class TickPoint(BaseModel):
    t: str
    p: float


class CandlePoint(BaseModel):
    time: str
    open: float
    high: float
    low: float
    close: float


class IndicatorPoint(BaseModel):
    time: str
    value: float


class DashboardResponse(BaseModel):
    status: str
    daily_pnl: float
    asset: str | None = None
    price_status: str = "live"
    position_qty: float = 0
    avg_entry_price: float = 0
    timeframe: str | None = None
    ma_short_period: int | None = None
    ma_long_period: int | None = None
    chart: list[CandlePoint]
    ma_short_series: list[IndicatorPoint] = []
    ma_long_series: list[IndicatorPoint] = []


class StrategyConfigIn(BaseModel):
    asset: str = Field(..., examples=["PETR4"])
    timeframe: str = Field(..., examples=["5M", "15M", "1H", "1D"])
    ma_short_period: int = Field(9, ge=1)
    ma_long_period: int = Field(21, ge=2)


class StrategyConfigOut(StrategyConfigIn):
    id: str
    updated_at: datetime


class BacktestMetrics(BaseModel):
    total_return: float
    win_rate: float
    max_drawdown: float
    sharpe_ratio: float
    insight_summary: str | None = None


class BacktestResponse(BaseModel):
    period_label: str
    metrics: BacktestMetrics
    equity_curve: list[float]
    equity_dates: list[str] = []
    price_chart: list[CandlePoint] = []
    ma_short_series: list[IndicatorPoint] = []
    ma_long_series: list[IndicatorPoint] = []


class BacktestRunIn(BaseModel):
    period_label: str = "6 Months"
    asset: str | None = None


class AssetUniverseOut(BaseModel):
    b3: list[str]
    crypto: list[str]
    all: list[str]


class LogIn(BaseModel):
    level: str
    message: str
    details: dict[str, Any] | None = None


class LogOut(BaseModel):
    id: int
    user_id: str | None = None
    level: str
    message: str
    details: dict[str, Any] | None = None
    created_at: datetime


class SettingsIn(BaseModel):
    api_key: str | None = None
    api_secret: str | None = None
    exchange_name: str = "binance"
    trade_mode: TradeModeEnum = TradeModeEnum.paper
    paper_trading: bool
    dark_mode: bool
    simulated_balance: float | None = Field(default=None, gt=0)


class SettingsOut(BaseModel):
    api_key_masked: str | None = None
    api_secret_masked: str | None = None
    exchange_name: str = "binance"
    trade_mode: TradeModeEnum = TradeModeEnum.paper
    paper_trading: bool
    dark_mode: bool
    simulated_balance: float
    updated_at: datetime


class PaperOrderIn(BaseModel):
    asset: str
    price: float
    quantity: float = Field(..., gt=0)


class PaperOrderOut(BaseModel):
    id: int
    side: str
    asset: str
    price: float
    quantity: float
    status: str
    created_at: datetime


class PaperStateResponse(BaseModel):
    balance: float
    focus_asset: str
    current_price: float
    price_status: str = "live"
    floating_pnl: float
    open_position_asset: str | None
    open_position_qty: float
    avg_entry_price: float
    recent_orders: list[PaperOrderOut]
