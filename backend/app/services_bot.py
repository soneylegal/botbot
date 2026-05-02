from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pandas as pd

from app import models, schemas
from app.config import BOT_AUTOMATION_INTERVAL_SECONDS
from app.core_unified import create_paper_order, get_or_create_settings, get_or_create_status, get_or_create_strategy
from app.db import SessionLocal
from app.services_exchange import ExchangeService


class BotAutomationState:
    def __init__(self):
        self.last_processed: dict[str, str] = {}


state = BotAutomationState()


def _latest_signal(asset: str, ma_short: int, ma_long: int, closes: list[float], times: list[datetime]) -> tuple[int, int, str | None]:
    if len(closes) < max(ma_long + 2, 30):
        return 0, 0, None

    df = pd.DataFrame({"close": closes}, index=pd.to_datetime(times, utc=True)).sort_index()
    df["ma_short"] = df["close"].rolling(ma_short).mean()
    df["ma_long"] = df["close"].rolling(ma_long).mean()
    df = df.dropna().copy()
    if len(df) < 2:
        return 0, 0, None

    prev = 1 if float(df["ma_short"].iloc[-2]) > float(df["ma_long"].iloc[-2]) else 0
    curr = 1 if float(df["ma_short"].iloc[-1]) > float(df["ma_long"].iloc[-1]) else 0
    ts = df.index[-1].isoformat()
    return prev, curr, ts


def _bot_automation_iteration_sync() -> None:
    db = SessionLocal()
    try:
        bot_status = get_or_create_status(db)
        if bot_status.status != "Running":
            return

        strategy = get_or_create_strategy(db)
        settings = get_or_create_settings(db)
        service = ExchangeService(settings)
        try:
            closes, times = service.fetch_historical_closes(strategy.asset, days=2)
        except ValueError:
            return

        prev_sig, curr_sig, ts = _latest_signal(
            strategy.asset,
            strategy.ma_short_period,
            strategy.ma_long_period,
            closes,
            times,
        )
        strategy_key = f"{strategy.asset}:{strategy.ma_short_period}:{strategy.ma_long_period}:{strategy.timeframe}"
        if ts is None or ts == state.last_processed.get(strategy_key):
            return

        crossover_up = prev_sig == 0 and curr_sig == 1
        crossover_down = prev_sig == 1 and curr_sig == 0
        if not (crossover_up or crossover_down):
            state.last_processed[strategy_key] = ts
            return

        users = db.query(models.User).filter(models.User.is_active.is_(True)).all()
        last_price = float(closes[-1]) if closes else 0.0
        if last_price <= 0:
            state.last_processed[strategy_key] = ts
            return

        for user in users:
            position = (
                db.query(models.UserPosition)
                .filter(
                    models.UserPosition.user_id == user.id,
                    models.UserPosition.asset == strategy.asset,
                    models.UserPosition.quantity > 0,
                )
                .first()
            )

            if crossover_up and (not position or float(position.quantity) == 0):
                balance_row = db.query(models.UserBalance).filter(models.UserBalance.user_id == user.id).first()
                if not balance_row or float(balance_row.balance) <= 10:
                    continue
                budget = min(float(balance_row.balance), 1000.0)
                qty = round(budget / last_price, 4)
                if qty <= 0:
                    continue
                create_paper_order(
                    db,
                    models.OrderSide.buy,
                    schemas.PaperOrderIn(asset=strategy.asset, price=last_price, quantity=qty),
                    user_id=user.id,
                )
                db.add(
                    models.LogEntry(
                        user_id=user.id,
                        level=models.LogLevel.info,
                        message="Bot executou ordem automatica devido ao cruzamento de medias",
                        details={
                            "asset": strategy.asset,
                            "signal": "buy",
                            "price": last_price,
                            "qty": qty,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        },
                    )
                )
                db.commit()

            if crossover_down and position and float(position.quantity) > 0:
                qty = float(position.quantity)
                create_paper_order(
                    db,
                    models.OrderSide.sell,
                    schemas.PaperOrderIn(asset=strategy.asset, price=last_price, quantity=qty),
                    user_id=user.id,
                )
                db.add(
                    models.LogEntry(
                        user_id=user.id,
                        level=models.LogLevel.info,
                        message="Bot executou ordem automatica devido ao cruzamento de medias",
                        details={
                            "asset": strategy.asset,
                            "signal": "sell",
                            "price": last_price,
                            "qty": qty,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        },
                    )
                )
                db.commit()

        state.last_processed[strategy_key] = ts
    finally:
        db.close()


async def bot_automation_loop(stop_event: asyncio.Event):
    while not stop_event.is_set():
        try:
            await asyncio.to_thread(_bot_automation_iteration_sync)
        except Exception:
            # protege loop de automacao contra queda total do processo
            pass

        await asyncio.sleep(BOT_AUTOMATION_INTERVAL_SECONDS)
