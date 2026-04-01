from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TickPoint(BaseModel):
    t: str
    p: float


class DashboardResponse(BaseModel):
    status: str
    daily_pnl: float
    asset: str | None = None
    chart: list[TickPoint]


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


class BacktestResponse(BaseModel):
    period_label: str
    metrics: BacktestMetrics
    equity_curve: list[float]


class LogIn(BaseModel):
    level: str
    message: str
    details: dict[str, Any] | None = None


class LogOut(BaseModel):
    id: int
    level: str
    message: str
    details: dict[str, Any] | None = None
    created_at: datetime


class SettingsIn(BaseModel):
    api_key: str | None = None
    api_secret: str | None = None
    paper_trading: bool
    dark_mode: bool


class SettingsOut(BaseModel):
    api_key_masked: str | None = None
    api_secret_masked: str | None = None
    paper_trading: bool
    dark_mode: bool
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
    open_position_asset: str | None
    open_position_qty: float
    recent_orders: list[PaperOrderOut]
