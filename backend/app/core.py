from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import math
import uuid

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app import models, schemas
from app.security import hash_password, verify_password
from app.services_backtest import run_ma_backtest
from app.services_exchange import ExchangeService


def _safe_float(value: float | int | Decimal | None, default: float = 0.0) -> float:
    try:
        v = float(value)
        return v if math.isfinite(v) else default
    except Exception:
        return default


def _round2(value: float | int | Decimal | None) -> float:
    return round(_safe_float(value), 2)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_decimal(value: float | int | str | Decimal) -> Decimal:
    return Decimal(str(value))


def mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 4:
        return "*" * len(value)
    return "*" * (len(value) - 4) + value[-4:]


def get_user_by_email(db: Session, email: str) -> models.User | None:
    return db.query(models.User).filter(models.User.email == email.lower()).first()


def create_user(db: Session, email: str, password: str) -> models.User:
    user = models.User(email=email.lower(), password_hash=hash_password(password), is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> models.User | None:
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def ensure_seed_admin(db: Session):
    user = get_user_by_email(db, "admin@botbot.local")
    if not user:
        create_user(db, "admin@botbot.local", "admin123")
        return
    if not user.password_hash.startswith("pbkdf2_sha256$"):
        user.password_hash = hash_password("admin123")
        db.commit()


def _append_log(
    db: Session,
    level: models.LogLevel,
    message: str,
    details: dict | None = None,
    user_id: uuid.UUID | None = None,
):
    db.add(models.LogEntry(level=level, message=message, details=details, user_id=user_id))


def get_or_create_status(db: Session) -> models.BotStatus:
    row = db.query(models.BotStatus).first()
    if row:
        return row

    row = models.BotStatus(status="Running", daily_pnl=Decimal("0.00"), current_asset="PETR4")
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_or_create_strategy(db: Session) -> models.StrategyConfig:
    row = db.query(models.StrategyConfig).order_by(desc(models.StrategyConfig.updated_at)).first()
    if row:
        return row

    row = models.StrategyConfig(asset="PETR4", timeframe="5M", ma_short_period=9, ma_long_period=21)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_or_create_settings(db: Session) -> models.AppSettings:
    row = db.query(models.AppSettings).first()
    if row:
        return row

    row = models.AppSettings(
        api_key_masked="********************",
        api_secret_masked="********************",
        paper_trading=True,
        dark_mode=True,
        exchange_name="binance",
        trade_mode=models.TradeMode.paper,
        simulated_balance=10000,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_or_create_user_balance(db: Session, user_id: uuid.UUID) -> models.UserBalance:
    row = db.query(models.UserBalance).filter(models.UserBalance.user_id == user_id).first()
    if row:
        return row

    user = db.query(models.User).filter(models.User.id == user_id).first()
    initial = _safe_float(user.balance if user else 10000, 10000)
    row = models.UserBalance(user_id=user_id, balance=_to_decimal(initial))
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_user_open_position(db: Session, user_id: uuid.UUID, asset: str | None = None) -> models.UserPosition | None:
    q = db.query(models.UserPosition).filter(models.UserPosition.user_id == user_id, models.UserPosition.quantity > 0)
    if asset:
        q = q.filter(models.UserPosition.asset == asset.upper())
    return q.order_by(desc(models.UserPosition.updated_at)).first()


def _to_candle_point(raw: dict | None) -> schemas.CandlePoint | None:
    if not raw:
        return None
    try:
        close = _safe_float(raw.get("close"), 0.0)
        if close <= 0:
            return None
        open_v = _safe_float(raw.get("open"), close)
        high_v = _safe_float(raw.get("high"), max(open_v, close))
        low_v = _safe_float(raw.get("low"), min(open_v, close))
        high_v = max(high_v, open_v, close)
        low_v = min(low_v, open_v, close)

        raw_time = str(raw.get("time") or "")
        parsed = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        else:
            parsed = parsed.astimezone(timezone.utc)

        return schemas.CandlePoint(
            time=parsed.isoformat(),
            open=float(open_v),
            high=float(high_v),
            low=float(low_v),
            close=float(close),
        )
    except Exception:
        return None


def _candles_from_ticks(ticks: list[models.MarketTick]) -> list[schemas.CandlePoint]:
    if not ticks:
        return []

    ticks_sorted = sorted(ticks, key=lambda t: t.tick_at)
    out: list[schemas.CandlePoint] = []
    for t in ticks_sorted:
        p = _safe_float(t.price, 0.0)
        if p <= 0:
            continue
        ts = t.tick_at
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        else:
            ts = ts.astimezone(timezone.utc)
        out.append(schemas.CandlePoint(time=ts.isoformat(), open=p, high=p, low=p, close=p))
    return out


def _build_ma_series(candles: list[schemas.CandlePoint], period: int | None) -> list[schemas.IndicatorPoint]:
    p = int(period or 0)
    if p <= 0 or len(candles) < p:
        return []

    closes = [float(c.close) for c in candles]
    out: list[schemas.IndicatorPoint] = []
    rolling_sum = 0.0
    for idx, value in enumerate(closes):
        rolling_sum += value
        if idx >= p:
            rolling_sum -= closes[idx - p]
        if idx >= p - 1:
            out.append(schemas.IndicatorPoint(time=candles[idx].time, value=rolling_sum / p))
    return out


def _period_days(period_label: str) -> int:
    mapping = {
        "1 Month": 30,
        "1M": 30,
        "1mo": 30,
        "6 Months": 180,
        "6M": 180,
        "6mo": 180,
        "1 Year": 365,
        "1Y": 365,
        "1y": 365,
    }
    return mapping.get(period_label, 180)


def _history_params_for_days(days: int) -> tuple[str, int]:
    if days <= 2:
        return "5m", 200
    if days <= 7:
        return "15m", 300
    if days <= 60:
        return "1h", 500
    return "1d", max(400, days)


def _resolve_spot_price(db: Session, asset: str, force_refresh: bool = False) -> tuple[float, str]:
    symbol = asset.upper()
    cached_tick = (
        db.query(models.MarketTick)
        .filter(models.MarketTick.asset == symbol)
        .order_by(desc(models.MarketTick.tick_at))
        .first()
    )

    if cached_tick and not force_refresh:
        ts = cached_tick.tick_at
        ts_utc = ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts.astimezone(timezone.utc)
        age = (_utc_now() - ts_utc).total_seconds()
        if age <= 30 and _safe_float(cached_tick.price, 0.0) > 0:
            return _safe_float(cached_tick.price), "Preço em Cache"

    settings = get_or_create_settings(db)
    service = ExchangeService(settings)
    live = _safe_float(service.fetch_spot_price(symbol, cache_ttl_seconds=20, db=db), 0.0)
    if live > 0:
        db.add(models.MarketTick(asset=symbol, price=live, volume=0, tick_at=_utc_now()))
        db.commit()
        return live, "Preço ao Vivo"

    if cached_tick and _safe_float(cached_tick.price, 0.0) > 0:
        return _safe_float(cached_tick.price), "Preço em Cache"

    raise ValueError(f"Preço indisponível para {symbol}")


def upsert_strategy(db: Session, payload: schemas.StrategyConfigIn, user_id: uuid.UUID | None = None) -> models.StrategyConfig:
    strategy = get_or_create_strategy(db)
    strategy.asset = payload.asset.upper()
    strategy.timeframe = payload.timeframe.upper()
    strategy.ma_short_period = payload.ma_short_period
    strategy.ma_long_period = payload.ma_long_period
    strategy.updated_at = _utc_now()

    status = get_or_create_status(db)
    status.current_asset = strategy.asset
    status.daily_pnl = Decimal("0.00")
    status.updated_at = _utc_now()
    ExchangeService.clear_spot_cache(strategy.asset)

    _append_log(
        db,
        models.LogLevel.info,
        f"Estratégia atualizada: {strategy.asset} ({strategy.timeframe})",
        {
            "asset": strategy.asset,
            "timeframe": strategy.timeframe,
            "ma_short_period": strategy.ma_short_period,
            "ma_long_period": strategy.ma_long_period,
        },
        user_id=user_id,
    )
    db.commit()
    db.refresh(strategy)
    return strategy


def get_dashboard_data(db: Session, user_id: uuid.UUID, include_chart: bool = True) -> schemas.DashboardResponse:
    strategy = get_or_create_strategy(db)
    status = get_or_create_status(db)
    asset = strategy.asset.upper()

    position = get_user_open_position(db, user_id=user_id, asset=asset)

    current_price = 0.0
    price_status = "Sem preço"
    try:
        current_price, price_status = _resolve_spot_price(db, asset, force_refresh=bool(position))
    except Exception:
        current_price, price_status = 0.0, "Sem preço"

    qty = _safe_float(position.quantity, 0.0) if position else 0.0
    avg = _safe_float(position.avg_entry_price, 0.0) if position else 0.0
    floating_pnl = (current_price - avg) * qty if current_price > 0 and avg > 0 and qty > 0 else 0.0

    status.daily_pnl = _to_decimal(_round2(floating_pnl))
    status.current_asset = asset
    status.updated_at = _utc_now()
    db.commit()

    chart: list[schemas.CandlePoint] = []
    if include_chart:
        min_points = max(180, strategy.ma_long_period * 6)
        settings = get_or_create_settings(db)
        service = ExchangeService(settings)
        raw = service.fetch_history(asset, timeframe=strategy.timeframe, limit=min_points, min_points=min_points)
        chart = [c for c in (_to_candle_point(x) for x in raw) if c]

        if not chart:
            ticks = (
                db.query(models.MarketTick)
                .filter(models.MarketTick.asset == asset)
                .order_by(desc(models.MarketTick.tick_at))
                .limit(min_points)
                .all()
            )
            chart = _candles_from_ticks(ticks)

        chart = sorted(chart, key=lambda c: c.time)
        if len(chart) > 300:
            chart = chart[-300:]

    return schemas.DashboardResponse(
        status="Running" if qty <= 0 else "Running (posição aberta)",
```#+#+#+#+assistant to=functions.read_file մեկնաբանություն  天天彩ացումները  北京赛车计划 to=functions.read_file  大发彩票官网ാത്തjson 招商总代{