"""Consolidated core business logic for the Swing Trade Bot.

This module replaces the former core.py, core2.py and crud.py files,
which contained duplicated and divergent implementations of the same
functions.  All routers and services should import from here.
"""

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


def _round4(value: float | int | Decimal | None) -> float:
    return round(_safe_float(value), 4)


def _fmt_money(value: float, asset: str) -> str:
    symbol = "US$" if asset.upper() in {"BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "DOGE", "TRX", "AVAX", "DOT"} else "R$"
    sign = "+" if value > 0 else ""
    return f"{sign}{symbol} {abs(_safe_float(value)):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


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


def _append_log(db: Session, level: models.LogLevel, message: str, details: dict | None = None, user_id: uuid.UUID | None = None):
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
        c = _safe_float(raw.get("close"), 0)
        if c <= 0:
            return None
        o = _safe_float(raw.get("open"), c)
        h = max(_safe_float(raw.get("high"), c), o, c)
        l = min(_safe_float(raw.get("low"), c), o, c)
        ts = datetime.fromisoformat(str(raw.get("time") or "").replace("Z", "+00:00"))
        ts = ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts.astimezone(timezone.utc)
        return schemas.CandlePoint(time=ts.isoformat(), open=o, high=h, low=l, close=c)
    except Exception:
        return None


def _build_ma_series(candles: list[schemas.CandlePoint], period: int | None) -> list[schemas.IndicatorPoint]:
    p = int(period or 0)
    if p <= 0 or len(candles) < p:
        return []
    closes = [float(c.close) for c in candles]
    out: list[schemas.IndicatorPoint] = []
    rolling = 0.0
    for i, v in enumerate(closes):
        rolling += v
        if i >= p:
            rolling -= closes[i - p]
        if i >= p - 1:
            out.append(schemas.IndicatorPoint(time=candles[i].time, value=rolling / p))
    return out


_TF_TO_SECONDS = {
    "1M": 60,
    "5M": 300,
    "15M": 900,
    "30M": 1800,
    "1H": 3600,
    "4H": 14400,
    "1D": 86400,
}


def _canonical_timeframe(value: str | None) -> str:
    raw = (value or "5M").strip().upper()
    aliases = {
        "1MIN": "1M",
        "5MIN": "5M",
        "15MIN": "15M",
        "30MIN": "30M",
        "60M": "1H",
        "1HR": "1H",
        "1HOUR": "1H",
    }
    return aliases.get(raw, raw if raw in _TF_TO_SECONDS else "5M")


def _timeframe_seconds(value: str | None) -> int:
    return _TF_TO_SECONDS.get(_canonical_timeframe(value), 300)


def _build_timeframe_candidates(preferred: str | None) -> list[str]:
    tf = _canonical_timeframe(preferred)
    matrix = {
        "1M": ["1M", "5M", "15M", "30M", "1H", "4H", "1D"],
        "5M": ["5M", "15M", "30M", "1H", "4H", "1D", "1M"],
        "15M": ["15M", "30M", "1H", "4H", "1D", "5M"],
        "30M": ["30M", "1H", "4H", "1D", "15M", "5M"],
        "1H": ["1H", "4H", "1D", "30M", "15M", "5M"],
        "4H": ["4H", "1D", "1H", "30M", "15M"],
        "1D": ["1D", "4H", "1H"],
    }
    return matrix.get(tf, ["5M", "15M", "1H", "4H", "1D"])


def _normalize_candles(
    candles: list[schemas.CandlePoint],
    timeframe: str,
    target_points: int,
) -> list[schemas.CandlePoint]:
    if not candles:
        return []

    step = _timeframe_seconds(timeframe)
    dedup: dict[int, schemas.CandlePoint] = {}
    for c in candles:
        try:
            ts = datetime.fromisoformat(c.time.replace("Z", "+00:00"))
            ts = ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts.astimezone(timezone.utc)
            bucket = int(ts.timestamp()) // step * step
            if c.close <= 0:
                continue
            dedup[bucket] = schemas.CandlePoint(
                time=datetime.fromtimestamp(bucket, tz=timezone.utc).isoformat(),
                open=float(c.open),
                high=float(max(c.high, c.open, c.close)),
                low=float(min(c.low, c.open, c.close)),
                close=float(c.close),
            )
        except Exception:
            continue

    ordered = sorted(dedup.items(), key=lambda x: x[0])
    if not ordered:
        return []

    out: list[schemas.CandlePoint] = []
    prev_bucket: int | None = None
    max_gap_fill = 60
    max_points = max(target_points * 2, 480)

    for bucket, candle in ordered:
        if prev_bucket is not None:
            missing = (bucket - prev_bucket) // step - 1
            if missing > 0:
                fill_count = min(missing, max_gap_fill, max(0, max_points - len(out) - 1))
                for i in range(fill_count):
                    fill_bucket = prev_bucket + step * (i + 1)
                    base = out[-1].close if out else candle.open
                    out.append(
                        schemas.CandlePoint(
                            time=datetime.fromtimestamp(fill_bucket, tz=timezone.utc).isoformat(),
                            open=float(base),
                            high=float(base),
                            low=float(base),
                            close=float(base),
                        )
                    )

        out.append(candle)
        prev_bucket = bucket

    if len(out) > max_points:
        out = out[-max_points:]
    return out


def _fetch_stable_candles(
    db: Session,
    asset: str,
    preferred_timeframe: str,
    min_points: int,
    limit: int,
) -> tuple[list[schemas.CandlePoint], str]:
    settings = get_or_create_settings(db)
    service = ExchangeService(settings)
    best: list[schemas.CandlePoint] = []
    best_tf = _canonical_timeframe(preferred_timeframe)

    for tf in _build_timeframe_candidates(preferred_timeframe):
        try:
            raw = service.fetch_history(asset, timeframe=tf, limit=limit, min_points=max(40, min_points // 2))
        except Exception:
            continue

        parsed = [c for c in (_to_candle_point(x) for x in raw) if c]
        normalized = _normalize_candles(parsed, tf, target_points=min_points)

        if len(normalized) > len(best):
            best = normalized
            best_tf = tf
        if len(normalized) >= min_points:
            return normalized, tf

    return best, best_tf


def _extract_last_two_closes(candles: list[schemas.CandlePoint]) -> tuple[float, float]:
    if len(candles) < 2:
        return 0.0, 0.0
    ordered = sorted(candles, key=lambda c: c.time)
    prev_close = _safe_float(ordered[-2].close, 0.0)
    last_close = _safe_float(ordered[-1].close, 0.0)
    return prev_close, last_close


def _compute_daily_asset_variation(db: Session, asset: str, current_price: float) -> tuple[float, float]:
    settings = get_or_create_settings(db)
    service = ExchangeService(settings)
    previous_close = 0.0

    try:
        day_candles = service.fetch_history(asset=asset, timeframe="1d", limit=3, min_points=2)
        valid = [c for c in (_to_candle_point(x) for x in day_candles) if c]
        if len(valid) >= 2:
            previous_close, _ = _extract_last_two_closes(valid)
    except Exception:
        previous_close = 0.0

    if previous_close <= 0:
        return 0.0, 0.0

    base = current_price if current_price > 0 else previous_close
    change_value = base - previous_close
    change_percent = (change_value / previous_close) * 100 if previous_close > 0 else 0.0
    return _round2(change_value), _round2(change_percent)


def _build_paper_insight(asset: str, qty: float, avg: float, current_price: float, pnl_value: float) -> tuple[str, str, str, float, float]:
    invested = _round2(avg * qty) if avg > 0 and qty > 0 else 0.0
    pnl_percent = _round2((pnl_value / invested) * 100) if invested > 0 else 0.0

    if qty <= 0:
        return (
            "Sem posição aberta",
            f"Você está líquido em {asset}. Abra uma posição para acompanhar ganho/perda em tempo real.",
            "neutral",
            invested,
            pnl_percent,
        )

    if current_price <= 0:
        return (
            "Preço indisponível",
            "Não foi possível atualizar o preço agora. Usaremos o último preço válido assim que disponível.",
            "warning",
            invested,
            pnl_percent,
        )

    if pnl_value > 0:
        return (
            "Você está no lucro",
            f"Você está lucrando {_fmt_money(pnl_value, asset)} ({pnl_percent:.2f}%). Se fechar a posição agora, este será o ganho realizado.",
            "success",
            invested,
            pnl_percent,
        )

    if pnl_value < 0:
        return (
            "Sua posição está em queda",
            f"Sua posição recua {abs(pnl_percent):.2f}% (perda de {_fmt_money(pnl_value, asset)}). O investimento inicial foi {_fmt_money(invested, asset)}.",
            "danger",
            invested,
            pnl_percent,
        )

    return (
        "No zero a zero",
        f"Sua posição está estável até agora. Investimento atual: {_fmt_money(invested, asset)}.",
        "neutral",
        invested,
        pnl_percent,
    )


def _resolve_spot_price(db: Session, asset: str, force_refresh: bool = False) -> tuple[float, str]:
    symbol = asset.upper()
    tick = db.query(models.MarketTick).filter(models.MarketTick.asset == symbol).order_by(desc(models.MarketTick.tick_at)).first()
    if tick and not force_refresh:
        ts = tick.tick_at.replace(tzinfo=timezone.utc) if tick.tick_at.tzinfo is None else tick.tick_at.astimezone(timezone.utc)
        if (_utc_now() - ts).total_seconds() <= 30 and _safe_float(tick.price) > 0:
            return _safe_float(tick.price), "Preço em Cache"

    settings = get_or_create_settings(db)
    service = ExchangeService(settings)
    live = _safe_float(service.fetch_spot_price(symbol, cache_ttl_seconds=20, db=db), 0)
    if live > 0:
        db.add(models.MarketTick(asset=symbol, price=live, volume=0, tick_at=_utc_now()))
        db.commit()
        return live, "Preço ao Vivo"

    if tick and _safe_float(tick.price) > 0:
        return _safe_float(tick.price), "Preço em Cache"
    raise ValueError("Preço indisponível")


def upsert_strategy(db: Session, payload: schemas.StrategyConfigIn, user_id: uuid.UUID | None = None) -> models.StrategyConfig:
    row = get_or_create_strategy(db)
    row.asset = payload.asset.upper()
    row.timeframe = payload.timeframe.upper()
    row.ma_short_period = payload.ma_short_period
    row.ma_long_period = payload.ma_long_period
    row.updated_at = _utc_now()

    status = get_or_create_status(db)
    status.current_asset = row.asset
    status.daily_pnl = _to_decimal(0)
    _append_log(db, models.LogLevel.info, f"Estratégia atualizada: {row.asset}", {"asset": row.asset}, user_id)
    db.commit()
    db.refresh(row)
    return row


def get_dashboard_data(db: Session, user_id: uuid.UUID, include_chart: bool = True) -> schemas.DashboardResponse:
    strategy = get_or_create_strategy(db)
    status = get_or_create_status(db)
    asset = strategy.asset.upper()
    position = get_user_open_position(db, user_id, asset=asset)

    try:
        current_price, price_status = _resolve_spot_price(db, asset, force_refresh=bool(position))
    except Exception:
        current_price, price_status = 0.0, "Sem preço"

    qty = _safe_float(position.quantity if position else 0)
    avg = _safe_float(position.avg_entry_price if position else 0)
    daily_change_value, daily_change_percent = _compute_daily_asset_variation(db, asset, current_price)

    status.daily_pnl = _to_decimal(_round2(daily_change_value))
    status.current_asset = asset
    status.updated_at = _utc_now()
    db.commit()

    chart: list[schemas.CandlePoint] = []
    used_timeframe = _canonical_timeframe(strategy.timeframe)
    if include_chart:
        min_points = max(120, int(strategy.ma_long_period or 21) * 5)
        chart, used_timeframe = _fetch_stable_candles(
            db,
            asset=asset,
            preferred_timeframe=strategy.timeframe,
            min_points=min_points,
            limit=max(280, min_points * 2),
        )
        chart = chart[-300:]

        if not chart:
            recent_ticks = (
                db.query(models.MarketTick)
                .filter(models.MarketTick.asset == asset)
                .order_by(desc(models.MarketTick.tick_at))
                .limit(min_points)
                .all()
            )
            synthetic = []
            for t in reversed(recent_ticks):
                p = _safe_float(t.price, 0.0)
                if p <= 0:
                    continue
                ts = t.tick_at.replace(tzinfo=timezone.utc) if t.tick_at.tzinfo is None else t.tick_at.astimezone(timezone.utc)
                synthetic.append(schemas.CandlePoint(time=ts.isoformat(), open=p, high=p, low=p, close=p))
            chart = _normalize_candles(synthetic, used_timeframe, target_points=min_points)[-300:]

    return schemas.DashboardResponse(
        status="Running",
        daily_pnl=_round2(daily_change_value),
        daily_change_percent=_round2(daily_change_percent),
        daily_change_value=_round2(daily_change_value),
        asset=asset,
        price_status=price_status,
        position_qty=_round4(qty),
        avg_entry_price=_round2(avg),
        timeframe=used_timeframe,
        ma_short_period=strategy.ma_short_period,
        ma_long_period=strategy.ma_long_period,
        chart=chart,
        ma_short_series=_build_ma_series(chart, strategy.ma_short_period) if include_chart else [],
        ma_long_series=_build_ma_series(chart, strategy.ma_long_period) if include_chart else [],
    )


def list_recent_paper_orders(db: Session, user_id: uuid.UUID, limit: int = 25) -> list[schemas.PaperOrderOut]:
    rows = db.query(models.PaperOrder).filter(models.PaperOrder.user_id == user_id).order_by(desc(models.PaperOrder.created_at)).limit(max(1, min(limit, 100))).all()
    return [schemas.PaperOrderOut(id=r.id, side=r.side.value, asset=r.asset, price=_safe_float(r.price), quantity=_safe_float(r.quantity), status=r.status.value, created_at=r.created_at) for r in rows]


def _period_days(label: str) -> int:
    return {"1mo": 30, "6mo": 180, "1y": 365, "1 Month": 30, "6 Months": 180, "1 Year": 365}.get(label, 180)


def _sample_aligned(values: list[float], labels: list[str], max_points: int = 100) -> tuple[list[float], list[str]]:
    if len(values) <= max_points:
        return values, labels[: len(values)]
    step = (len(values) - 1) / (max_points - 1)
    idx = [round(i * step) for i in range(max_points)]
    return [values[i] for i in idx], [labels[i] for i in idx]


def run_backtest(db: Session, period_label: str = "6 Months", user_id: uuid.UUID | None = None, asset: str | None = None) -> schemas.BacktestResponse:
    strategy = get_or_create_strategy(db)
    selected = (asset or strategy.asset).upper()
    days = _period_days(period_label)
    min_points = max(80, strategy.ma_long_period + 24)

    try:
        candles, used_timeframe = _fetch_stable_candles(
            db,
            asset=selected,
            preferred_timeframe=strategy.timeframe,
            min_points=min_points,
            limit=max(320, days * 2),
        )
        if len(candles) < min_points:
            raise ValueError("Dados históricos insuficientes para este ativo no momento")

        closes: list[float] = []
        times: list[datetime] = []
        for candle in candles:
            close = _safe_float(candle.close, 0.0)
            if close <= 0:
                continue
            closes.append(close)
            times.append(datetime.fromisoformat(candle.time.replace("Z", "+00:00")))

        if len(closes) < min_points:
            raise ValueError("Dados históricos insuficientes para este ativo no momento")

        initial = 10000.0
        if user_id:
            initial = max(_safe_float(get_or_create_user_balance(db, user_id).balance, 10000), 1.0)

        result = run_ma_backtest(closes, times, strategy.ma_short_period, strategy.ma_long_period, initial_capital=initial)

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
        db.commit()
        db.refresh(row)

        sampled_curve, sampled_dates = _sample_aligned([float(v) for v in result["equity_curve"]], [str(v) for v in result.get("equity_timestamps", [])], 120)
        chart = candles[-240:]
        tone = "success" if _safe_float(row.total_return) > 0 else "danger" if _safe_float(row.total_return) < 0 else "neutral"
        return schemas.BacktestResponse(
            period_label=row.period_label,
            metrics=schemas.BacktestMetrics(
                total_return=_round2(row.total_return),
                win_rate=_round2(row.win_rate),
                max_drawdown=_round2(row.max_drawdown),
                sharpe_ratio=_round2(row.sharpe_ratio),
                insight_summary=f"Backtest concluído com OHLC ({used_timeframe}). Resultado do período: {_round2(row.total_return):.2f}%.",
                insight_tone=tone,
            ),
            equity_curve=[_round2(v) for v in sampled_curve],
            equity_dates=sampled_dates,
            price_chart=chart,
            ma_short_series=_build_ma_series(chart, strategy.ma_short_period),
            ma_long_series=_build_ma_series(chart, strategy.ma_long_period),
        )
    except ValueError:
        return schemas.BacktestResponse(
            period_label=period_label,
            metrics=schemas.BacktestMetrics(
                total_return=0.0,
                win_rate=0.0,
                max_drawdown=0.0,
                sharpe_ratio=0.0,
                insight_summary="Dados históricos insuficientes para este ativo no momento.",
                insight_tone="warning",
            ),
            equity_curve=[],
            equity_dates=[],
            price_chart=[],
            ma_short_series=[],
            ma_long_series=[],
        )
    except Exception:
        return schemas.BacktestResponse(
            period_label=period_label,
            metrics=schemas.BacktestMetrics(
                total_return=0.0,
                win_rate=0.0,
                max_drawdown=0.0,
                sharpe_ratio=0.0,
                insight_summary="Dados históricos insuficientes para este ativo no momento.",
                insight_tone="warning",
            ),
            equity_curve=[],
            equity_dates=[],
            price_chart=[],
            ma_short_series=[],
            ma_long_series=[],
        )


def get_latest_backtest(db: Session, user_id: uuid.UUID | None = None) -> schemas.BacktestResponse:
    row = db.query(models.BacktestResult).order_by(desc(models.BacktestResult.created_at)).first()
    if not row:
        return run_backtest(db, user_id=user_id)
    return run_backtest(db, period_label=row.period_label, user_id=user_id)


def list_logs(db: Session, user_id: uuid.UUID, limit: int = 100) -> list[models.LogEntry]:
    return db.query(models.LogEntry).filter(models.LogEntry.user_id == user_id).order_by(desc(models.LogEntry.created_at)).limit(limit).all()


def create_log(db: Session, payload: schemas.LogIn, user_id: uuid.UUID) -> models.LogEntry:
    level = models.LogLevel(payload.level)
    item = models.LogEntry(level=level, message=payload.message, details=payload.details, user_id=user_id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_settings(db: Session, payload: schemas.SettingsIn, user_id: uuid.UUID | None = None) -> models.AppSettings:
    settings = get_or_create_settings(db)
    settings.paper_trading = payload.paper_trading
    settings.dark_mode = payload.dark_mode
    settings.exchange_name = payload.exchange_name
    settings.trade_mode = models.TradeMode(payload.trade_mode.value)

    if payload.simulated_balance and float(payload.simulated_balance) > 0:
        settings.simulated_balance = _to_decimal(payload.simulated_balance)
        if user_id:
            bal = get_or_create_user_balance(db, user_id)
            bal.balance = _to_decimal(payload.simulated_balance)
            user = db.query(models.User).filter(models.User.id == user_id).first()
            if user:
                user.balance = _to_decimal(payload.simulated_balance)

    if payload.api_key:
        settings.api_key = payload.api_key
        settings.api_key_masked = mask_secret(payload.api_key)
    if payload.api_secret:
        settings.api_secret = payload.api_secret
        settings.api_secret_masked = mask_secret(payload.api_secret)

    settings.updated_at = _utc_now()
    db.commit()
    db.refresh(settings)
    return settings


def _get_or_create_position(db: Session, user_id: uuid.UUID, asset: str) -> models.UserPosition:
    row = db.query(models.UserPosition).filter(models.UserPosition.user_id == user_id, models.UserPosition.asset == asset).with_for_update().first()
    if row:
        return row
    row = models.UserPosition(user_id=user_id, asset=asset, quantity=0, avg_entry_price=0)
    db.add(row)
    db.flush()
    return row


def create_paper_order(db: Session, side: models.OrderSide, payload: schemas.PaperOrderIn, user_id: uuid.UUID) -> models.PaperOrder:
    asset = payload.asset.upper()
    strategy = get_or_create_strategy(db)
    if strategy.asset.upper() != asset:
        raise ValueError("Operações permitidas apenas no ativo da estratégia ativa.")

    price = _safe_float(payload.price, 0)
    qty = _safe_float(payload.quantity, 0)
    if price <= 0 or qty <= 0:
        raise ValueError("Preço e quantidade devem ser maiores que zero.")

    balance = db.query(models.UserBalance).filter(models.UserBalance.user_id == user_id).with_for_update().first()
    if not balance:
        balance = models.UserBalance(user_id=user_id, balance=_to_decimal(10000))
        db.add(balance)
        db.flush()

    pos = _get_or_create_position(db, user_id, asset)
    value = _to_decimal(price) * _to_decimal(qty)

    if side == models.OrderSide.buy:
        if _to_decimal(balance.balance) < value:
            raise ValueError("Saldo insuficiente para compra.")
        prev_q = _to_decimal(pos.quantity)
        prev_avg = _to_decimal(pos.avg_entry_price or 0)
        next_q = prev_q + _to_decimal(qty)
        pos.avg_entry_price = ((prev_q * prev_avg) + (_to_decimal(qty) * _to_decimal(price))) / next_q
        pos.quantity = next_q
        balance.balance = _to_decimal(balance.balance) - value
    else:
        if _to_decimal(pos.quantity) < _to_decimal(qty):
            raise ValueError("Quantidade de venda maior que a posição atual.")
        next_q = _to_decimal(pos.quantity) - _to_decimal(qty)
        pos.quantity = next_q
        if next_q <= 0:
            pos.avg_entry_price = _to_decimal(0)
        balance.balance = _to_decimal(balance.balance) + value

    order = models.PaperOrder(user_id=user_id, side=side, asset=asset, price=price, quantity=qty, status=models.OrderStatus.filled, simulated=True)
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def create_live_or_paper_order(db: Session, side: models.OrderSide, payload: schemas.PaperOrderIn, user_id: uuid.UUID) -> models.PaperOrder:
    safe_price = _safe_float(payload.price, 0)
    if safe_price <= 0:
        safe_price, _ = _resolve_spot_price(db, payload.asset)
        payload = schemas.PaperOrderIn(asset=payload.asset.upper(), price=safe_price, quantity=payload.quantity)

    settings = get_or_create_settings(db)
    if settings.trade_mode == models.TradeMode.live:
        ExchangeService(settings).create_live_order(
            symbol=f"{payload.asset.upper()}/USDT",
            side=side.value,
            amount=float(payload.quantity),
            price=float(payload.price),
        )
        # Mesmo em live, mantemos livro local sincronizado para P/L/posições no app.
        order = create_paper_order(db, side, payload, user_id)
        order.simulated = False
        db.commit()
        db.refresh(order)
        return order

    return create_paper_order(db, side, payload, user_id)


def get_paper_state(db: Session, user_id: uuid.UUID, focus_asset: str | None = None) -> schemas.PaperStateResponse:
    _ = focus_asset
    strategy = get_or_create_strategy(db)
    asset = strategy.asset.upper()
    bal = get_or_create_user_balance(db, user_id)
    pos = get_user_open_position(db, user_id, asset=asset)
    try:
        current_price, price_status = _resolve_spot_price(db, asset, force_refresh=True)
    except Exception:
        current_price, price_status = 0.0, "Sem preço"

    qty = _safe_float(pos.quantity if pos else 0)
    avg = _safe_float(pos.avg_entry_price if pos else 0)
    pnl = (current_price - avg) * qty if current_price > 0 and avg > 0 and qty > 0 else 0
    insight_title, insight_message, insight_tone, invested_capital, pnl_percent = _build_paper_insight(
        asset=asset,
        qty=qty,
        avg=avg,
        current_price=current_price,
        pnl_value=pnl,
    )

    return schemas.PaperStateResponse(
        balance=_round2(bal.balance),
        focus_asset=asset,
        current_price=_round2(current_price),
        price_status=price_status,
        floating_pnl=_round2(pnl),
        floating_pnl_percent=_round2(pnl_percent),
        invested_capital=_round2(invested_capital),
        open_position_asset=asset if qty > 0 else None,
        open_position_qty=_round4(qty),
        avg_entry_price=_round2(avg),
        insight_title=insight_title,
        insight_message=insight_message,
        insight_tone=insight_tone,
        recent_orders=list_recent_paper_orders(db, user_id, 25),
    )


def close_open_position(db: Session, user_id: uuid.UUID) -> models.PaperOrder:
    asset = get_or_create_strategy(db).asset.upper()
    pos = _get_or_create_position(db, user_id, asset)
    qty = _safe_float(pos.quantity, 0)
    if qty <= 0:
        raise ValueError("Sem posição aberta para fechar.")
    price, _ = _resolve_spot_price(db, asset, force_refresh=True)
    return create_live_or_paper_order(db, models.OrderSide.sell, schemas.PaperOrderIn(asset=asset, price=price, quantity=qty), user_id)


def reset_paper_wallet(db: Session, user_id: uuid.UUID, initial_balance: float | None = None) -> schemas.PaperStateResponse:
    settings = get_or_create_settings(db)
    target = _safe_float(initial_balance, _safe_float(settings.simulated_balance, 10000))
    if target <= 0:
        target = 10000

    bal = db.query(models.UserBalance).filter(models.UserBalance.user_id == user_id).with_for_update().first()
    if not bal:
        bal = models.UserBalance(user_id=user_id, balance=_to_decimal(target))
        db.add(bal)
    else:
        bal.balance = _to_decimal(target)

    db.query(models.UserPosition).filter(models.UserPosition.user_id == user_id).delete(synchronize_session=False)
    db.query(models.PaperOrder).filter(models.PaperOrder.user_id == user_id).delete(synchronize_session=False)
    db.commit()
    return get_paper_state(db, user_id)


def test_exchange_connection(db: Session, user_id: uuid.UUID | None = None) -> tuple[bool, str]:
    settings = get_or_create_settings(db)
    if settings.trade_mode == models.TradeMode.paper:
        return True, "Paper mode ativo."
    if not settings.api_key or not settings.api_secret:
        return False, "Credenciais ausentes para modo live."
    price = ExchangeService(settings).fetch_last_price("BTC/USDT")
    if not price:
        return False, "Falha ao conectar na exchange live."
    return True, "Conexão live validada com sucesso."
