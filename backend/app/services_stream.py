from __future__ import annotations

import asyncio
import random
from datetime import datetime, timezone

from fastapi import WebSocket
from sqlalchemy.orm import Session

from app.config import MARKET_STREAM_INTERVAL_SECONDS
from app.db import SessionLocal
from app.models import AppSettings, BotStatus, MarketTick
from app.services_exchange import ExchangeService


class ConnectionManager:
    def __init__(self):
        self.connections: dict[str, set[WebSocket]] = {}

    async def connect(self, asset: str, websocket: WebSocket):
        await websocket.accept()
        self.connections.setdefault(asset, set()).add(websocket)

    def disconnect(self, asset: str, websocket: WebSocket):
        if asset in self.connections and websocket in self.connections[asset]:
            self.connections[asset].remove(websocket)

    async def broadcast(self, asset: str, payload: dict):
        peers = list(self.connections.get(asset, set()))
        for ws in peers:
            try:
                await ws.send_json(payload)
            except Exception:
                self.disconnect(asset, ws)


manager = ConnectionManager()


def _current_asset(db: Session) -> str:
    status = db.query(BotStatus).first()
    return (status.current_asset if status else None) or "PETR4"


def _insert_tick(db: Session, asset: str, price: float) -> MarketTick:
    tick = MarketTick(asset=asset, price=price, volume=random.uniform(500, 5000), tick_at=datetime.now(timezone.utc))
    db.add(tick)
    db.commit()
    db.refresh(tick)
    return tick


def _next_price(db: Session, asset: str) -> float:
    settings = db.query(AppSettings).first()
    live_price = None
    if settings:
        service = ExchangeService(settings)
        symbol = f"{asset}/USDT"
        live_price = service.fetch_last_price(symbol)

    if live_price and live_price > 0:
        return live_price

    last = db.query(MarketTick).filter(MarketTick.asset == asset).order_by(MarketTick.tick_at.desc()).first()
    base = float(last.price) if last else 25.0
    return max(0.1, base + random.uniform(-0.35, 0.45))


async def market_stream_loop(stop_event: asyncio.Event):
    while not stop_event.is_set():
        db = SessionLocal()
        try:
            asset = _current_asset(db)
            price = _next_price(db, asset)
            tick = _insert_tick(db, asset, price)
            await manager.broadcast(
                asset,
                {
                    "asset": asset,
                    "price": float(tick.price),
                    "volume": float(tick.volume),
                    "tick_at": tick.tick_at.isoformat(),
                },
            )
        finally:
            db.close()

        await asyncio.sleep(MARKET_STREAM_INTERVAL_SECONDS)
