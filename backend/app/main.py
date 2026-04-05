from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import WebSocket, WebSocketDisconnect

from app.config import API_TITLE, API_VERSION
from app.crud import ensure_seed_admin
from app.db import Base, SessionLocal, apply_runtime_migrations, engine
from app.models import AppSettings, MarketTick
from app.routers import auth, backtest, dashboard, logs, paper, settings, strategy
from app.services_exchange import ExchangeService
from app.services_stream import manager

app = FastAPI(title=API_TITLE, version=API_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    Base.metadata.create_all(bind=engine)
    apply_runtime_migrations()
    db = SessionLocal()
    try:
        ensure_seed_admin(db)
    finally:
        db.close()

@app.get("/health")
def health():
    return {"ok": True}


@app.websocket("/ws/market/{asset}")
async def market_ws(websocket: WebSocket, asset: str):
    asset = asset.upper()
    await manager.connect(asset, websocket)
    try:
        while True:
            await websocket.receive_text()

            db = SessionLocal()
            try:
                settings = db.query(AppSettings).first()
                price = None
                if settings:
                    service = ExchangeService(settings)
                    price = service.fetch_spot_price(asset)

                if not price or float(price) <= 0:
                    last_tick = (
                        db.query(MarketTick)
                        .filter(MarketTick.asset == asset)
                        .order_by(MarketTick.tick_at.desc())
                        .first()
                    )
                    price = float(last_tick.price) if last_tick and float(last_tick.price) > 0 else 1.0

                db.add(MarketTick(asset=asset, price=float(price), volume=0, tick_at=datetime.now(timezone.utc)))
                db.commit()

                await manager.broadcast(
                    asset,
                    {
                        "asset": asset,
                        "price": float(price),
                        "volume": 0.0,
                        "tick_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
            finally:
                db.close()
    except WebSocketDisconnect:
        manager.disconnect(asset, websocket)
    except Exception:
        manager.disconnect(asset, websocket)


app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(strategy.router)
app.include_router(backtest.router)
app.include_router(logs.router)
app.include_router(settings.router)
app.include_router(paper.router)
