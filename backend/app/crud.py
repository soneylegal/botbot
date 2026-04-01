from datetime import datetime, timedelta
from decimal import Decimal
import random

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app import models, schemas


def mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 4:
        return "*" * len(value)
    return "*" * (len(value) - 4) + value[-4:]


def get_or_create_status(db: Session) -> models.BotStatus:
    status = db.query(models.BotStatus).first()
    if not status:
        status = models.BotStatus(status="Running", daily_pnl=Decimal("0.00"), current_asset="PETR4")
        db.add(status)
        db.commit()
        db.refresh(status)
    return status


def get_or_create_strategy(db: Session) -> models.StrategyConfig:
    strategy = db.query(models.StrategyConfig).order_by(desc(models.StrategyConfig.updated_at)).first()
    if not strategy:
        strategy = models.StrategyConfig(asset="PETR4", timeframe="5M", ma_short_period=9, ma_long_period=21)
        db.add(strategy)
        db.commit()
        db.refresh(strategy)
    return strategy


def upsert_strategy(db: Session, payload: schemas.StrategyConfigIn) -> models.StrategyConfig:
    strategy = get_or_create_strategy(db)
    strategy.asset = payload.asset
    strategy.timeframe = payload.timeframe
    strategy.ma_short_period = payload.ma_short_period
    strategy.ma_long_period = payload.ma_long_period
    strategy.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(strategy)
    return strategy


def get_dashboard_data(db: Session) -> schemas.DashboardResponse:
    status = get_or_create_status(db)
    ticks = (
        db.query(models.MarketTick)
        .filter(models.MarketTick.asset == (status.current_asset or "PETR4"))
        .order_by(desc(models.MarketTick.tick_at))
        .limit(30)
        .all()
    )

    if not ticks:
        base = 25.0
        now = datetime.utcnow()
        for i in range(30):
            tick = models.MarketTick(
                asset=status.current_asset or "PETR4",
                price=base + random.uniform(-0.4, 0.4) + (i * 0.05),
                volume=1000 + random.uniform(0, 300),
                tick_at=now - timedelta(minutes=30 - i),
            )
            db.add(tick)
        db.commit()
        ticks = (
            db.query(models.MarketTick)
            .filter(models.MarketTick.asset == (status.current_asset or "PETR4"))
            .order_by(desc(models.MarketTick.tick_at))
            .limit(30)
            .all()
        )

    chart = [schemas.TickPoint(t=t.tick_at.isoformat(), p=float(t.price)) for t in reversed(ticks)]
    return schemas.DashboardResponse(
        status=status.status,
        daily_pnl=float(status.daily_pnl),
        asset=status.current_asset,
        chart=chart,
    )


def get_latest_backtest(db: Session) -> schemas.BacktestResponse:
    item = db.query(models.BacktestResult).order_by(desc(models.BacktestResult.created_at)).first()
    if not item:
        equity = [10000, 10150, 10300, 10280, 10600, 10800, 10700, 11050, 11550]
        item = models.BacktestResult(
            period_label="6 Months",
            total_return=15.5,
            win_rate=62.0,
            max_drawdown=-8.2,
            sharpe_ratio=1.4,
            equity_curve=equity,
        )
        db.add(item)
        db.commit()
        db.refresh(item)

    return schemas.BacktestResponse(
        period_label=item.period_label,
        metrics=schemas.BacktestMetrics(
            total_return=float(item.total_return),
            win_rate=float(item.win_rate),
            max_drawdown=float(item.max_drawdown),
            sharpe_ratio=float(item.sharpe_ratio),
        ),
        equity_curve=[float(v) for v in item.equity_curve],
    )


def list_logs(db: Session, limit: int = 100) -> list[models.LogEntry]:
    return db.query(models.LogEntry).order_by(desc(models.LogEntry.created_at)).limit(limit).all()


def create_log(db: Session, payload: schemas.LogIn) -> models.LogEntry:
    item = models.LogEntry(level=payload.level, message=payload.message, details=payload.details)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def get_or_create_settings(db: Session) -> models.AppSettings:
    settings = db.query(models.AppSettings).first()
    if not settings:
        settings = models.AppSettings(
            api_key_masked="********************",
            api_secret_masked="********************",
            paper_trading=True,
            dark_mode=True,
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def update_settings(db: Session, payload: schemas.SettingsIn) -> models.AppSettings:
    settings = get_or_create_settings(db)
    settings.paper_trading = payload.paper_trading
    settings.dark_mode = payload.dark_mode
    if payload.api_key:
        settings.api_key_masked = mask_secret(payload.api_key)
    if payload.api_secret:
        settings.api_secret_masked = mask_secret(payload.api_secret)
    settings.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(settings)
    return settings


def get_or_create_paper_account(db: Session) -> models.PaperAccount:
    account = db.query(models.PaperAccount).first()
    if not account:
        account = models.PaperAccount(balance=10000, open_position_asset="PETR4", open_position_qty=0)
        db.add(account)
        db.commit()
        db.refresh(account)
    return account


def create_paper_order(db: Session, side: models.OrderSide, payload: schemas.PaperOrderIn) -> models.PaperOrder:
    account = get_or_create_paper_account(db)
    value = Decimal(str(payload.price)) * Decimal(str(payload.quantity))

    if side == models.OrderSide.buy:
        account.balance = Decimal(account.balance) - value
        account.open_position_asset = payload.asset
        account.open_position_qty = Decimal(account.open_position_qty) + Decimal(str(payload.quantity))
    else:
        account.balance = Decimal(account.balance) + value
        account.open_position_asset = payload.asset
        account.open_position_qty = max(Decimal("0"), Decimal(account.open_position_qty) - Decimal(str(payload.quantity)))

    order = models.PaperOrder(
        side=side,
        asset=payload.asset,
        price=payload.price,
        quantity=payload.quantity,
        status=models.OrderStatus.filled,
        simulated=True,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def get_paper_state(db: Session) -> schemas.PaperStateResponse:
    account = get_or_create_paper_account(db)
    orders = db.query(models.PaperOrder).order_by(desc(models.PaperOrder.created_at)).limit(10).all()
    mapped_orders = [
        schemas.PaperOrderOut(
            id=o.id,
            side=o.side.value,
            asset=o.asset,
            price=float(o.price),
            quantity=float(o.quantity),
            status=o.status.value,
            created_at=o.created_at,
        )
        for o in orders
    ]
    return schemas.PaperStateResponse(
        balance=float(account.balance),
        open_position_asset=account.open_position_asset,
        open_position_qty=float(account.open_position_qty),
        recent_orders=mapped_orders,
    )
