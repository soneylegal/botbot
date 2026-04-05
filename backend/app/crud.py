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


def mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 4:
        return "*" * len(value)
    return "*" * (len(value) - 4) + value[-4:]

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


    def list_recent_paper_orders(db: Session, user_id: uuid.UUID, limit: int = 25) -> list[schemas.PaperOrderOut]:
        rows = (
            db.query(models.PaperOrder)
            .filter(models.PaperOrder.user_id == user_id)
            .order_by(desc(models.PaperOrder.created_at))
            .limit(max(1, min(limit, 100)))
            .all()
        )
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


        # ---------- Auth ----------
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


        def list_recent_paper_orders(db: Session, user_id: uuid.UUID, limit: int = 25) -> list[schemas.PaperOrderOut]:
            rows = (
                db.query(models.PaperOrder)
                .filter(models.PaperOrder.user_id == user_id)
                .order_by(desc(models.PaperOrder.created_at))
                .limit(max(1, min(limit, 100)))
                .all()
            )
        return [
            schemas.PaperOrderOut(
                id=r.id,
                side=r.side.value,
                asset=r.asset,
                price=_safe_float(r.price),
                quantity=_safe_float(r.quantity),
                status=r.status.value,
                created_at=r.created_at,
            )
            for r in rows
        ]


        def get_latest_backtest(db: Session, user_id: uuid.UUID | None = None) -> schemas.BacktestResponse:
            row = db.query(models.BacktestResult).order_by(desc(models.BacktestResult.created_at)).first()
            if not row:
                return run_backtest(db, period_label="6 Months", user_id=user_id)

            strategy = get_or_create_strategy(db)
            settings = get_or_create_settings(db)
            service = ExchangeService(settings)
            raw = service.fetch_history(strategy.asset.upper(), timeframe=strategy.timeframe, limit=240, min_points=80)
            candles = [c for c in (_to_candle_point(x) for x in raw) if c]

            equity_curve = [float(v) for v in (row.equity_curve or [])]
            now = _utc_now()
            synthetic_dates = [(now - timedelta(days=len(equity_curve) - 1 - i)).date().isoformat() for i in range(len(equity_curve))]
            sampled_curve, sampled_dates = _sample_aligned(equity_curve, synthetic_dates, max_points=120)

            return schemas.BacktestResponse(
                period_label=row.period_label,
                metrics=schemas.BacktestMetrics(
                    total_return=_round2(row.total_return),
                    win_rate=_round2(row.win_rate),
                    max_drawdown=_round2(row.max_drawdown),
                    sharpe_ratio=_round2(row.sharpe_ratio),
                    insight_summary="Último backtest salvo em banco para a estratégia ativa.",
                ),
                equity_curve=[_round2(v) for v in sampled_curve],
                equity_dates=sampled_dates,
                price_chart=candles,
                ma_short_series=_build_ma_series(candles, strategy.ma_short_period),
                ma_long_series=_build_ma_series(candles, strategy.ma_long_period),
            )



    def get_latest_backtest(db: Session, user_id: uuid.UUID | None = None) -> schemas.BacktestResponse:
        row = db.query(models.BacktestResult).order_by(desc(models.BacktestResult.created_at)).first()
        if not row:
            return run_backtest(db, period_label="6 Months", user_id=user_id)

        strategy = get_or_create_strategy(db)
        settings = get_or_create_settings(db)
        service = ExchangeService(settings)
        raw = service.fetch_history(strategy.asset.upper(), timeframe=strategy.timeframe, limit=240, min_points=80)
        candles = [c for c in (_to_candle_point(x) for x in raw) if c]

        equity_curve = [float(v) for v in (row.equity_curve or [])]
        now = _utc_now()
        synthetic_dates = [(now - timedelta(days=len(equity_curve) - 1 - i)).date().isoformat() for i in range(len(equity_curve))]
        sampled_curve, sampled_dates = _sample_aligned(equity_curve, synthetic_dates, max_points=120)

        return schemas.BacktestResponse(
            period_label=row.period_label,
            metrics=schemas.BacktestMetrics(
                total_return=_round2(row.total_return),
                win_rate=_round2(row.win_rate),
                max_drawdown=_round2(row.max_drawdown),
                sharpe_ratio=_round2(row.sharpe_ratio),
                insight_summary="Último backtest salvo em banco para a estratégia ativa.",
            ),
            equity_curve=[_round2(v) for v in sampled_curve],
            equity_dates=sampled_dates,
            price_chart=candles,
            ma_short_series=_build_ma_series(candles, strategy.ma_short_period),
            ma_long_series=_build_ma_series(candles, strategy.ma_long_period),
        )

# ---------- Auth ----------
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


def get_or_create_status(db: Session) -> models.BotStatus:
    status = db.query(models.BotStatus).first()
    if not status:
        status = models.BotStatus(status="Running", daily_pnl=Decimal("0.00"), current_asset="PETR4")
        db.add(status)
        db.commit()
        db.refresh(status)
    return status


def get_or_create_user_balance(db: Session, user_id: uuid.UUID) -> models.UserBalance:
    balance = db.query(models.UserBalance).filter(models.UserBalance.user_id == user_id).first()
    if not balance:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        user_balance = float(user.balance) if user and user.balance is not None else 10000
        balance = models.UserBalance(user_id=user_id, balance=user_balance)
        db.add(balance)
        db.commit()
        db.refresh(balance)
    return balance


def get_user_open_position(db: Session, user_id: uuid.UUID) -> models.UserPosition | None:
    return (
        db.query(models.UserPosition)
        .filter(models.UserPosition.user_id == user_id, models.UserPosition.quantity > 0)
        .order_by(desc(models.UserPosition.updated_at))
        .first()
    )


def get_or_create_strategy(db: Session) -> models.StrategyConfig:
    strategy = db.query(models.StrategyConfig).order_by(desc(models.StrategyConfig.updated_at)).first()
    if not strategy:
        strategy = models.StrategyConfig(asset="PETR4", timeframe="5M", ma_short_period=9, ma_long_period=21)
        db.add(strategy)
        db.commit()
        db.refresh(strategy)
    return strategy


def _append_log(
    db: Session,
    level: models.LogLevel,
    message: str,
    details: dict | None = None,
    user_id: uuid.UUID | None = None,
):
    try:
        normalized_level = level if isinstance(level, models.LogLevel) else models.LogLevel(str(level))
        db.add(models.LogEntry(level=normalized_level, message=message, details=details, user_id=user_id))
    except Exception:
        db.rollback()


def _sample_points(values: list[float], max_points: int = 100) -> list[float]:
    if len(values) <= max_points:
        return values
    step = (len(values) - 1) / (max_points - 1)
    return [values[round(i * step)] for i in range(max_points)]


def _sample_aligned(values: list[float], labels: list[str], max_points: int = 100) -> tuple[list[float], list[str]]:
    if len(values) <= max_points:
        return values, labels[: len(values)]
    step = (len(values) - 1) / (max_points - 1)
    idxs = [round(i * step) for i in range(max_points)]
    return [values[i] for i in idxs], [labels[i] if i < len(labels) else "" for i in idxs]


def _safe_number(value: float | int | None, default: float = 0.0) -> float:
    try:
        v = float(value)
        return v if math.isfinite(v) else default
    except Exception:
        return default


def _round2(value: float | int | None) -> float:
    return round(_safe_number(value, 0.0), 2)


def _sanitize_text(value: str) -> str:
    try:
        return value.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore").replace("�", "")
    except Exception:
        return ""


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
        return "15m", 240
    if days <= 60:
        return "1h", 360
    return "1d", max(90, days)


def _to_candle_row(raw: dict | None) -> schemas.CandlePoint | None:
    if not raw:
        return None
    try:
        time_raw = str(raw.get("time") or "")
        close = _safe_number(raw.get("close"), 0.0)
        if close <= 0:
            return None
        open_v = _safe_number(raw.get("open"), close)
        high_v = _safe_number(raw.get("high"), max(open_v, close))
        low_v = _safe_number(raw.get("low"), min(open_v, close))
        high_v = max(high_v, open_v, close)
        low_v = min(low_v, open_v, close)
        return schemas.CandlePoint(
            time=time_raw,
            open=_round2(open_v),
            high=_round2(high_v),
            low=_round2(low_v),
            close=_round2(close),
        )
    except Exception:
        return None


def _build_candles_from_ticks(ticks: list[models.MarketTick]) -> list[schemas.CandlePoint]:
    candles: list[schemas.CandlePoint] = []
    for t in reversed(ticks):
        price = _safe_number(float(t.price), 0.0)
        if price <= 0:
            continue
        iso = t.tick_at.isoformat()
        candles.append(
            schemas.CandlePoint(
                time=iso,
                open=_round2(price),
                high=_round2(price),
                low=_round2(price),
                close=_round2(price),
            )
        )
    return candles


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
            out.append(
                schemas.IndicatorPoint(
                    time=candles[idx].time,
                    value=_round2(rolling_sum / p),
                )
            )
    return out


def upsert_strategy(
    db: Session,
    payload: schemas.StrategyConfigIn,
    user_id: uuid.UUID | None = None,
) -> models.StrategyConfig:
    strategy = get_or_create_strategy(db)
    strategy.asset = payload.asset
    strategy.timeframe = payload.timeframe
    strategy.ma_short_period = payload.ma_short_period
    strategy.ma_long_period = payload.ma_long_period
    strategy.updated_at = datetime.now(timezone.utc)

    status = get_or_create_status(db)
    status.current_asset = payload.asset
    status.daily_pnl = Decimal("0.00")
    status.status = "Running"
    ExchangeService.clear_spot_cache()

    _append_log(
        db,
        models.LogLevel.info,
        f"Estratégia atualizada para {payload.asset} ({payload.timeframe})",
        {
            "asset": payload.asset,
            "timeframe": payload.timeframe,
            "ma_short_period": payload.ma_short_period,
            "ma_long_period": payload.ma_long_period,
        },
        user_id=user_id,
    )

    db.commit()
    db.refresh(strategy)
    return strategy


def get_dashboard_data(
    db: Session,
    user_id: uuid.UUID,
    include_chart: bool = True,
) -> schemas.DashboardResponse:
    try:
        db.rollback()
    except Exception:
        pass

    status = get_or_create_status(db)
    strategy = get_or_create_strategy(db)
    open_positions = (
        db.query(models.UserPosition)
        .filter(models.UserPosition.user_id == user_id, models.UserPosition.quantity > 0)
        .order_by(desc(models.UserPosition.updated_at))
        .all()
    )
    asset_to_show = (strategy.asset or status.current_asset or "PETR4").upper()
    primary_position = next((p for p in open_positions if p.asset.upper() == asset_to_show), None)

    latest_price_for_chart = 0.0
    price_status = "Preço em Cache"
    try:
        latest_price_for_chart, price_status = _resolve_spot_price(db, asset_to_show)
    except Exception:
        latest_price_for_chart = 0.0

    target_candles = max(100, int(strategy.ma_long_period or 0) * 4)
    ticks = (
        db.query(models.MarketTick)
        .filter(models.MarketTick.asset == asset_to_show)
        .order_by(desc(models.MarketTick.tick_at))
        .limit(max(target_candles, 120))
        .all()
    )

    history_points: list[dict] = []
    if include_chart and len(ticks) < target_candles:
        try:
            settings_dash = get_or_create_settings(db)
            service_dash = ExchangeService(settings_dash)
            history_points = service_dash.fetch_history(
                asset_to_show,
                timeframe=strategy.timeframe or "5m",
                limit=target_candles,
                min_points=target_candles,
            )
            if history_points:
                persisted_ticks = []
                for pt in history_points:
                    raw_close = _safe_number(pt.get("close"), 0.0)
                    if raw_close <= 0:
                        continue
                    raw_time = str(pt.get("time") or "")
                    try:
                        tick_ts = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
                    except Exception:
                        tick_ts = datetime.now(timezone.utc)
                    persisted_ticks.append(
                        models.MarketTick(asset=asset_to_show, price=raw_close, tick_at=tick_ts)
                    )
                if persisted_ticks:
                    db.add_all(persisted_ticks)
                    db.commit()
                    ticks = (
                        db.query(models.MarketTick)
                        .filter(models.MarketTick.asset == asset_to_show)
                        .order_by(desc(models.MarketTick.tick_at))
                        .limit(max(target_candles, 120))
                        .all()
                    )
        except Exception:
            db.rollback()

    daily_pnl = 0.0
    status_text = status.status
    price_status = "Preço em Cache" if (not ticks and latest_price_for_chart <= 0) else price_status

    position_for_pnl = primary_position
    if position_for_pnl and float(position_for_pnl.quantity or 0) > 0:
        pnl_asset = asset_to_show
        try:
            spot_price, _ = _resolve_spot_price(db, pnl_asset, force_refresh=True)
        except Exception:
            pos_tick = (
                db.query(models.MarketTick)
                .filter(models.MarketTick.asset == pnl_asset)
                .order_by(desc(models.MarketTick.tick_at))
                .first()
            )
            spot_price = _safe_number(float(pos_tick.price), 0.0) if pos_tick else 0.0

        qty = float(position_for_pnl.quantity or 0)
        entry = float(position_for_pnl.avg_entry_price or 0)
        if spot_price > 0 and qty > 0 and entry > 0:
            daily_pnl = (spot_price - entry) * qty
            status.daily_pnl = Decimal(str(_round2(daily_pnl)))
        status_text = "Running (posição aberta)" if status.status == "Running" else status.status

    chart: list[schemas.CandlePoint] = []
    if include_chart:
        chart = _build_candles_from_ticks(ticks)

    if include_chart and history_points:
        parsed_history = [c for c in (_to_candle_row(pt) for pt in history_points) if c]
        if len(parsed_history) >= max(len(chart), target_candles):
            chart = parsed_history

    if include_chart and len(chart) < target_candles and latest_price_for_chart > 0:
        now = datetime.now(timezone.utc)
        chart = [
            schemas.CandlePoint(
                time=(now - timedelta(minutes=(target_candles - 1 - i))).isoformat(),
                open=_round2(latest_price_for_chart),
                high=_round2(latest_price_for_chart),
                low=_round2(latest_price_for_chart),
                close=_round2(latest_price_for_chart),
            )
            for i in range(target_candles)
        ]

    ma_short_series = _build_ma_series(chart, strategy.ma_short_period) if include_chart else []
    ma_long_series = _build_ma_series(chart, strategy.ma_long_period) if include_chart else []

    db.commit()

    return schemas.DashboardResponse(
        status=status_text,
        daily_pnl=_round2(daily_pnl),
        asset=asset_to_show,
        price_status=price_status,
        position_qty=_round2((float(primary_position.quantity) if primary_position else 0.0)),
        avg_entry_price=_round2((float(primary_position.avg_entry_price) if primary_position else 0.0)),
        timeframe=strategy.timeframe,
        ma_short_period=strategy.ma_short_period,
        ma_long_period=strategy.ma_long_period,
        chart=chart,
        ma_short_series=ma_short_series,
        ma_long_series=ma_long_series,
    )


def list_recent_paper_orders(
    db: Session,
    user_id: uuid.UUID,
    limit: int = 25,
) -> list[schemas.PaperOrderOut]:
    rows = (
        db.query(models.PaperOrder)
        .filter(models.PaperOrder.user_id == user_id)
        .order_by(desc(models.PaperOrder.created_at))
        .limit(max(1, min(limit, 100)))
        .all()
    )
    return [
        schemas.PaperOrderOut(
            id=row.id,
            side=row.side.value,
            asset=row.asset,
            price=float(row.price),
            quantity=float(row.quantity),
            status=row.status.value,
            created_at=row.created_at,
        )
        for row in rows
    ]


def get_latest_backtest(db: Session, user_id: uuid.UUID | None = None) -> schemas.BacktestResponse:
    item = db.query(models.BacktestResult).order_by(desc(models.BacktestResult.created_at)).first()
    if not item:
        return run_backtest(db, period_label="6 Months", user_id=user_id)

    sampled_curve = [_round2(v) for v in _sample_points([float(v) for v in item.equity_curve], 100)]
    synthetic_dates = []
    if sampled_curve:
        now = datetime.now(timezone.utc)
        synthetic_dates = [
            (now - timedelta(days=(len(sampled_curve) - 1 - i))).date().isoformat() for i in range(len(sampled_curve))
        ]

    strategy = get_or_create_strategy(db)
    price_chart: list[schemas.CandlePoint] = []
    try:
        settings = get_or_create_settings(db)
        service = ExchangeService(settings)
        tf = strategy.timeframe or "5m"
        raw_candles = service.fetch_history(strategy.asset.upper(), timeframe=tf, limit=180, min_points=30)
        price_chart = [c for c in (_to_candle_row(row) for row in raw_candles) if c]
    except Exception:
        price_chart = []

    if not price_chart:
        raise ValueError("Sem histórico real para montar o gráfico do backtest.")

    insight_summary = "Métricas calculadas sobre histórico real de fechamento com estratégia de cruzamento de médias móveis."
    ma_short_series = _build_ma_series(price_chart, strategy.ma_short_period)
    ma_long_series = _build_ma_series(price_chart, strategy.ma_long_period)
    return schemas.BacktestResponse(
        period_label=item.period_label,
        metrics=schemas.BacktestMetrics(
            total_return=_round2(item.total_return),
            win_rate=_round2(item.win_rate),
            max_drawdown=_round2(item.max_drawdown),
            sharpe_ratio=_round2(item.sharpe_ratio),
            insight_summary=insight_summary,
        ),
        equity_curve=sampled_curve,
        equity_dates=synthetic_dates,
        price_chart=price_chart,
        ma_short_series=ma_short_series,
        ma_long_series=ma_long_series,
    )


def run_backtest(
    db: Session,
    period_label: str = "6 Months",
    user_id: uuid.UUID | None = None,
    asset: str | None = None,
) -> schemas.BacktestResponse:
    strategy = get_or_create_strategy(db)
    selected_asset = (asset or strategy.asset).upper()
    days = _period_days(period_label)
    min_points = max(strategy.ma_long_period + 5, 40)

    settings = get_or_create_settings(db)
    service = ExchangeService(settings)
    history_tf, history_limit = _history_params_for_days(days)
    if strategy.timeframe:
        history_tf = strategy.timeframe

    raw_candles = service.fetch_history(
        selected_asset,
        timeframe=history_tf,
        limit=max(history_limit, min_points * 2),
        min_points=min_points,
    )

    # Mapeamento explícito OHLCV -> série de fechamentos para o motor matemático.
    prices: list[float] = []
    times: list[datetime] = []
    for candle in raw_candles:
        try:
            close = _safe_number(candle.get("close"), 0.0)
            if close <= 0:
                continue
            raw_time = str(candle.get("time") or "")
            ts = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            else:
                ts = ts.astimezone(timezone.utc)
            prices.append(close)
            times.append(ts)
        except Exception:
            continue

    price_chart = [c for c in (_to_candle_row(row) for row in raw_candles) if c]

    if len(prices) < min_points:
        recent_ticks = (
            db.query(models.MarketTick)
            .filter(models.MarketTick.asset == selected_asset)
            .order_by(models.MarketTick.tick_at.asc())
            .limit(2000)
            .all()
        )
        prices = [_safe_number(float(t.price), 0.0) for t in recent_ticks if _safe_number(float(t.price), 0.0) > 0]
        times = [t.tick_at if t.tick_at.tzinfo else t.tick_at.replace(tzinfo=timezone.utc) for t in recent_ticks if _safe_number(float(t.price), 0.0) > 0]

    if not price_chart and prices and times:
        price_chart = [
            schemas.CandlePoint(
                time=(t if t.tzinfo else t.replace(tzinfo=timezone.utc)).isoformat(),
                open=_round2(prices[max(i - 1, 0)]),
                high=_round2(max(prices[max(i - 1, 0)], prices[i])),
                low=_round2(min(prices[max(i - 1, 0)], prices[i])),
                close=_round2(prices[i]),
            )
            for i, t in enumerate(times)
        ]

    if len(prices) < min_points:
        raise ValueError("Dados insuficientes para este período")

    # Obriga a capturar do saldo real do banco, sem inventar "10000.0"
    initial_capital = 0.0
    if user_id:
        balance_row = db.query(models.UserBalance).filter(models.UserBalance.user_id == user_id).first()
        if balance_row and float(balance_row.balance) > 0:
            initial_capital = float(balance_row.balance)
            
    if initial_capital <= 0:
        if settings.simulated_balance is not None and float(settings.simulated_balance) > 0:
            initial_capital = float(settings.simulated_balance)
        else:
            raise ValueError("O usuário não possui saldo definido para iniciar o backtest.")

    result = run_ma_backtest(
        prices,
        times,
        strategy.ma_short_period,
        strategy.ma_long_period,
        initial_capital=initial_capital,
    )

    row = models.BacktestResult(
        strategy_config_id=strategy.id,
        period_label=period_label,
        total_return=result["total_return"],
        win_rate=result["win_rate"],
        max_drawdown=result["max_drawdown"],
        sharpe_ratio=result["sharpe_ratio"],
        equity_curve=result["equity_curve"],
    )
    db.add(row)
    _append_log(
        db,
        models.LogLevel.success,
        f"Backtest executado: {selected_asset} ({period_label})",
        {
            "asset": selected_asset,
            "period_label": period_label,
            "total_return": result["total_return"],
            "win_rate": result["win_rate"],
            "max_drawdown": result["max_drawdown"],
            "sharpe_ratio": result["sharpe_ratio"],
        },
        user_id=user_id,
    )
    db.commit()
    db.refresh(row)

    sampled_curve_raw, sampled_dates = _sample_aligned(
        [float(v) for v in result["equity_curve"]],
        [str(ts) for ts in result.get("equity_timestamps", [])],
        100,
    )

    insight_summary = "A estratégia apresenta um Retorno Total de {return_pct}% no período, com uma Taxa de Acerto (Win Rate) de {win_rate}%. O Rebaixamento Máximo (Max Drawdown) de {drawdown}% indica o maior risco enfrentado. O Índice Sharpe de {sharpe} avalia a relação risco-retorno.".format(
        return_pct=_round2(row.total_return),
        win_rate=_round2(row.win_rate),
        drawdown=_round2(row.max_drawdown),
        sharpe=_round2(row.sharpe_ratio)
    )

    return schemas.BacktestResponse(
        period_label=row.period_label,
        metrics=schemas.BacktestMetrics(
            total_return=_round2(row.total_return),
            win_rate=_round2(row.win_rate),
            max_drawdown=_round2(row.max_drawdown),
            sharpe_ratio=_round2(row.sharpe_ratio),
            insight_summary=insight_summary,
        ),
        equity_curve=[_round2(v) for v in sampled_curve_raw],
        equity_dates=sampled_dates,
        price_chart=price_chart,
        ma_short_series=_build_ma_series(price_chart, strategy.ma_short_period),
        ma_long_series=_build_ma_series(price_chart, strategy.ma_long_period),
    )


def list_logs(db: Session, user_id: uuid.UUID, limit: int = 100) -> list[models.LogEntry]:
    return (
        db.query(models.LogEntry)
        .filter(models.LogEntry.user_id == user_id)
        .order_by(desc(models.LogEntry.created_at))
        .limit(limit)
        .all()
    )


def create_log(db: Session, payload: schemas.LogIn, user_id: uuid.UUID) -> models.LogEntry:
    level = models.LogLevel(payload.level)
    item = models.LogEntry(level=level, message=payload.message, details=payload.details, user_id=user_id)
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
            exchange_name="binance",
            trade_mode=models.TradeMode.paper,
            simulated_balance=10000,
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def update_settings(
    db: Session,
    payload: schemas.SettingsIn,
    user_id: uuid.UUID | None = None,
) -> models.AppSettings:
    settings = get_or_create_settings(db)
    settings.paper_trading = payload.paper_trading
    settings.dark_mode = payload.dark_mode
    settings.exchange_name = payload.exchange_name
    settings.trade_mode = models.TradeMode(payload.trade_mode.value)
    if payload.simulated_balance and float(payload.simulated_balance) > 0:
        settings.simulated_balance = Decimal(str(payload.simulated_balance))
        if user_id:
            balance_row = db.query(models.UserBalance).filter(models.UserBalance.user_id == user_id).first()
            if not balance_row:
                balance_row = models.UserBalance(user_id=user_id, balance=Decimal(str(payload.simulated_balance)))
                db.add(balance_row)
                db.flush()
            balance_row.balance = Decimal(str(payload.simulated_balance))
            user = db.query(models.User).filter(models.User.id == user_id).first()
            if user:
                user.balance = Decimal(str(payload.simulated_balance))
    if payload.api_key:
        settings.api_key = payload.api_key
        settings.api_key_masked = mask_secret(payload.api_key)
    if payload.api_secret:
        settings.api_secret = payload.api_secret
        settings.api_secret_masked = mask_secret(payload.api_secret)
    settings.updated_at = datetime.now(timezone.utc)
    _append_log(
        db,
        models.LogLevel.info,
        "Configurações atualizadas",
        {
            "exchange_name": payload.exchange_name,
            "trade_mode": payload.trade_mode.value,
            "paper_trading": payload.paper_trading,
            "dark_mode": payload.dark_mode,
            "simulated_balance": float(settings.simulated_balance),
        },
        user_id=user_id,
    )
    db.commit()
    db.refresh(settings)
    return settings


def _get_or_create_user_position(db: Session, user_id: uuid.UUID, asset: str) -> models.UserPosition:
    position = (
        db.query(models.UserPosition)
        .filter(models.UserPosition.user_id == user_id, models.UserPosition.asset == asset)
        .first()
    )
    if not position:
        position = models.UserPosition(user_id=user_id, asset=asset, quantity=0, avg_entry_price=0)
        db.add(position)
        db.flush()
    return position


def create_paper_order(
    db: Session,
    side: models.OrderSide,
    payload: schemas.PaperOrderIn,
    user_id: uuid.UUID,
) -> models.PaperOrder:
    balance_row = (
        db.query(models.UserBalance)
        .filter(models.UserBalance.user_id == user_id)
        .with_for_update()
        .first()
    )
    if not balance_row:
        balance_row = models.UserBalance(user_id=user_id, balance=10000)
        db.add(balance_row)
        db.flush()

    position_row = (
        db.query(models.UserPosition)
        .filter(models.UserPosition.user_id == user_id, models.UserPosition.asset == payload.asset)
        .with_for_update()
        .first()
    )
    if not position_row:
        position_row = models.UserPosition(user_id=user_id, asset=payload.asset, quantity=0, avg_entry_price=0)
        db.add(position_row)
        db.flush()

    value = Decimal(str(payload.price)) * Decimal(str(payload.quantity))

    if side == models.OrderSide.buy:
        if Decimal(balance_row.balance) < value:
            raise ValueError("Saldo insuficiente para compra.")

        other_open = (
            db.query(models.UserPosition)
            .filter(
                models.UserPosition.user_id == user_id,
                models.UserPosition.asset != payload.asset,
                models.UserPosition.quantity > 0,
            )
            .first()
        )
        if other_open:
            raise ValueError("Já existe posição aberta em outro ativo. Venda antes de comprar novo ativo.")

        prev_qty = Decimal(position_row.quantity)
        prev_avg = Decimal(position_row.avg_entry_price or 0)
        buy_qty = Decimal(str(payload.quantity))
        buy_price = Decimal(str(payload.price))

        balance_row.balance = Decimal(balance_row.balance) - value
        position_row.quantity = prev_qty + buy_qty
        if position_row.quantity > 0:
            total_cost = (prev_qty * prev_avg) + (buy_qty * buy_price)
            position_row.avg_entry_price = total_cost / position_row.quantity
    else:
        if Decimal(position_row.quantity) <= 0:
            raise ValueError("Sem posição aberta para venda neste ativo.")
        if Decimal(position_row.quantity) < Decimal(str(payload.quantity)):
            raise ValueError("Quantidade de venda maior que a posição aberta.")

        balance_row.balance = Decimal(balance_row.balance) + value
        position_row.quantity = max(Decimal("0"), Decimal(position_row.quantity) - Decimal(str(payload.quantity)))
        if Decimal(position_row.quantity) == 0:
            position_row.avg_entry_price = Decimal("0")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        user.balance = balance_row.balance

    legacy_account = db.query(models.PaperAccount).first()
    if not legacy_account:
        legacy_account = models.PaperAccount(balance=10000, open_position_asset=None, open_position_qty=0)
        db.add(legacy_account)
        db.flush()
    legacy_account.balance = balance_row.balance
    legacy_account.open_position_asset = payload.asset if Decimal(position_row.quantity) > 0 else None
    legacy_account.open_position_qty = position_row.quantity

    order = models.PaperOrder(
        user_id=user_id,
        side=side,
        asset=payload.asset,
        price=payload.price,
        quantity=payload.quantity,
        status=models.OrderStatus.filled,
        simulated=True,
    )
    db.add(order)
    db.flush()

    _append_log(
        db,
        models.LogLevel.success,
        f"Ordem simulada executada: {side.value.upper()} {payload.quantity} {payload.asset} @ {payload.price}",
        {
            "side": side.value,
            "asset": payload.asset,
            "price": payload.price,
            "quantity": payload.quantity,
            "simulated": True,
        },
        user_id=user_id,
    )
    db.commit()
    db.refresh(order)
    return order


def create_live_or_paper_order(
    db: Session,
    side: models.OrderSide,
    payload: schemas.PaperOrderIn,
    user_id: uuid.UUID,
) -> models.PaperOrder:
    if float(payload.price or 0) <= 0:
        try:
            fallback_price, _ = _resolve_spot_price(db, payload.asset)
        except ValueError:
            fallback_price = 0.0
        if fallback_price > 0:
            payload = schemas.PaperOrderIn(asset=payload.asset, price=float(fallback_price), quantity=payload.quantity)
        else:
            last_tick = (
                db.query(models.MarketTick)
                .filter(models.MarketTick.asset == payload.asset.upper())
                .order_by(models.MarketTick.tick_at.desc())
                .first()
            )
            if last_tick and float(last_tick.price or 0) > 0:
                payload = schemas.PaperOrderIn(asset=payload.asset, price=float(last_tick.price), quantity=payload.quantity)

    if float(payload.price or 0) <= 0:
        raise ValueError("Preço indisponível para este ativo no momento.")

    settings = get_or_create_settings(db)
    if settings.trade_mode == models.TradeMode.live:
        symbol = f"{payload.asset}/USDT"
        service = ExchangeService(settings)
        service.create_live_order(symbol=symbol, side=side.value, amount=payload.quantity, price=payload.price)
        order = models.PaperOrder(
            user_id=user_id,
            side=side,
            asset=payload.asset,
            price=payload.price,
            quantity=payload.quantity,
            status=models.OrderStatus.filled,
            simulated=False,
        )
        db.add(order)
        _append_log(
            db,
            models.LogLevel.success,
            f"Ordem live enviada: {side.value.upper()} {payload.quantity} {payload.asset} @ {payload.price}",
            {
                "side": side.value,
                "asset": payload.asset,
                "price": payload.price,
                "quantity": payload.quantity,
                "simulated": False,
            },
            user_id=user_id,
        )
        db.commit()
        db.refresh(order)
        return order

    return create_paper_order(db, side, payload, user_id=user_id)


def _resolve_spot_price(db: Session, asset: str, force_refresh: bool = False) -> tuple[float, str]:
    asset = asset.upper()
    latest_tick = (
        db.query(models.MarketTick)
        .filter(models.MarketTick.asset == asset)
        .order_by(models.MarketTick.tick_at.desc())
        .first()
    )

    last_saved_price = _safe_number(float(latest_tick.price), 0.0) if latest_tick else None
    last_tick_age_seconds: float | None = None
    if latest_tick:
        tick_at = latest_tick.tick_at
        if tick_at.tzinfo is None:
            tick_at = tick_at.replace(tzinfo=timezone.utc)
        else:
            tick_at = tick_at.astimezone(timezone.utc)
        now_utc = datetime.now(timezone.utc)
        last_tick_age_seconds = (now_utc - tick_at).total_seconds()
        if last_tick_age_seconds <= 60 and not force_refresh:
            return _safe_number(float(latest_tick.price), 0.0), "Preço em Cache"

    try:
        settings = get_or_create_settings(db)
        service = ExchangeService(settings)
        price = service.fetch_spot_price(asset, cache_ttl_seconds=60, db=db)
        safe_price = _safe_number(price, 0.0)
        if safe_price > 0:
            db.add(models.MarketTick(asset=asset, price=safe_price, volume=0, tick_at=datetime.now(timezone.utc)))
            _append_log(
                db,
                models.LogLevel.info,
                f"Buscando preço real para {asset}... Resultado: {_round2(safe_price)}",
                {"asset": asset, "price": _round2(safe_price)},
            )
            db.commit()
            return _round2(safe_price), "Preço ao Vivo"
    except Exception:
        db.rollback()

    if last_saved_price and last_saved_price > 0:
        return _round2(last_saved_price), "Preço em Cache"

    # regra rígida: sem inventar preço (nada de 1.0)
    raise ValueError(f"Preço indisponível para {asset}. Sem cotação ao vivo e sem tick em cache.")


def get_paper_state(db: Session, user_id: uuid.UUID, focus_asset: str | None = None) -> schemas.PaperStateResponse:
    balance_row = get_or_create_user_balance(db, user_id)
    open_position = get_user_open_position(db, user_id)
    strategy = get_or_create_strategy(db)
    strategy_asset = (strategy.asset or "PETR4").upper()
    asset = (focus_asset or strategy_asset).upper()
    if focus_asset:
        ExchangeService.clear_spot_cache(asset)
    try:
        current_price, price_status = _resolve_spot_price(db, asset, force_refresh=bool(open_position and float(open_position.quantity) > 0))
    except ValueError:
        current_price, price_status = 0.0, "Sem cache para o ativo"

    floating_pnl = 0.0
    if open_position and float(open_position.quantity) > 0:
        position_asset = open_position.asset.upper()
        if position_asset == asset:
            position_price = current_price
        else:
            try:
                position_price, _ = _resolve_spot_price(db, position_asset, force_refresh=True)
            except Exception:
                db.rollback()
                position_price = 0.0
        if position_price and position_price > 0:
            floating_pnl = (position_price - float(open_position.avg_entry_price or 0)) * float(open_position.quantity)

    orders = (
        db.query(models.PaperOrder)
        .filter(models.PaperOrder.user_id == user_id)
        .order_by(desc(models.PaperOrder.created_at))
        .limit(10)
        .all()
    )
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
        balance=_round2(balance_row.balance),
        focus_asset=asset,
        current_price=_round2(current_price),
        price_status=price_status,
        floating_pnl=_round2(floating_pnl),
        open_position_asset=(open_position.asset if open_position else None),
        open_position_qty=(float(open_position.quantity) if open_position else 0.0),
        avg_entry_price=_round2((float(open_position.avg_entry_price) if open_position else 0.0)),
        recent_orders=mapped_orders,
    )


def close_open_position(db: Session, user_id: uuid.UUID) -> models.PaperOrder:
    open_position = (
        db.query(models.UserPosition)
        .filter(models.UserPosition.user_id == user_id, models.UserPosition.quantity > 0)
        .order_by(desc(models.UserPosition.updated_at))
        .with_for_update()
        .first()
    )
    if not open_position or float(open_position.quantity) <= 0:
        _append_log(
            db,
            models.LogLevel.warning,
            "Tentativa de fechar posição sem ativo em foco",
            {"reason": "no_open_position"},
            user_id=user_id,
        )
        db.commit()
        raise ValueError("Sem posição aberta para fechar.")

    sell_price, _ = _resolve_spot_price(db, open_position.asset, force_refresh=True)
    if not sell_price or sell_price <= 0:
        _append_log(
            db,
            models.LogLevel.error,
            "Tentativa de fechar posição sem preço disponível",
            {
                "reason": "quote_unavailable",
                "asset": open_position.asset,
                "qty": float(open_position.quantity),
            },
            user_id=user_id,
        )
        db.commit()
        raise ValueError(
            "Não foi possível obter preço atual do ativo (provedor indisponível/rate limit). Tente novamente em instantes."
        )

    payload = schemas.PaperOrderIn(
        asset=open_position.asset,
        price=float(sell_price),
        quantity=float(open_position.quantity),
    )
    try:
        return create_live_or_paper_order(db, models.OrderSide.sell, payload, user_id=user_id)
    except Exception as exc:
        _append_log(
            db,
            models.LogLevel.error,
            "Erro de banco ao fechar posição",
            {
                "reason": "db_error",
                "asset": open_position.asset,
                "qty": float(open_position.quantity),
                "error": _sanitize_text(str(exc)),
            },
            user_id=user_id,
        )
        db.commit()
        raise ValueError("Erro de banco ao fechar posição") from exc


def reset_paper_wallet(db: Session, user_id: uuid.UUID, initial_balance: float | None = None) -> schemas.PaperStateResponse:
    settings = get_or_create_settings(db)
    target_balance = float(initial_balance) if (initial_balance is not None and float(initial_balance) > 0) else float(settings.simulated_balance or 10000)
    balance_row = (
        db.query(models.UserBalance)
        .filter(models.UserBalance.user_id == user_id)
        .with_for_update()
        .first()
    )
    if not balance_row:
        balance_row = models.UserBalance(user_id=user_id, balance=Decimal(str(target_balance)))
        db.add(balance_row)
        db.flush()
    else:
        balance_row.balance = Decimal(str(target_balance))

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        user.balance = Decimal(str(target_balance))

    db.query(models.UserPosition).filter(models.UserPosition.user_id == user_id).delete(synchronize_session=False)
    db.query(models.PaperOrder).filter(
        models.PaperOrder.user_id == user_id,
        models.PaperOrder.simulated.is_(True),
    ).delete(synchronize_session=False)

    legacy_account = db.query(models.PaperAccount).first()
    if not legacy_account:
        legacy_account = models.PaperAccount(balance=Decimal(str(target_balance)), open_position_asset=None, open_position_qty=0)
        db.add(legacy_account)
    else:
        legacy_account.balance = Decimal(str(target_balance))
        legacy_account.open_position_asset = None
        legacy_account.open_position_qty = Decimal("0")

    _append_log(
        db,
        models.LogLevel.warning,
        "Carteira paper resetada manualmente",
        {"initial_balance": target_balance},
        user_id=user_id,
    )
    db.commit()
    return get_paper_state(db, user_id=user_id)


def test_exchange_connection(db: Session, user_id: uuid.UUID | None = None) -> tuple[bool, str]:
    settings = get_or_create_settings(db)
    if settings.trade_mode == models.TradeMode.paper:
        _append_log(db, models.LogLevel.info, "Teste de conexão em modo paper", {"mode": "paper"}, user_id=user_id)
        db.commit()
        return True, "Paper mode ativo. Conexão externa não requerida."

    if not settings.api_key or not settings.api_secret:
        _append_log(
            db,
            models.LogLevel.error,
            "Teste de conexão live falhou por ausência de credenciais",
            user_id=user_id,
        )
        db.commit()
        return False, "Credenciais ausentes para modo live."

    service = ExchangeService(settings)
    price = service.fetch_last_price("BTC/USDT")
    if not price:
        _append_log(db, models.LogLevel.error, "Falha ao conectar na exchange live", user_id=user_id)
        db.commit()
        return False, "Falha ao conectar na exchange live."
    _append_log(
        db,
        models.LogLevel.success,
        "Conexão live validada com sucesso",
        {"probe_symbol": "BTC/USDT"},
        user_id=user_id,
    )
    db.commit()
    return True, "Conexão live validada com sucesso."
