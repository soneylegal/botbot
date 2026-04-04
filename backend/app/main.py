import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import WebSocket, WebSocketDisconnect

from app.config import API_TITLE, API_VERSION
from app.crud import ensure_seed_admin
from app.db import Base, SessionLocal, apply_runtime_migrations, engine
from app.routers import auth, backtest, dashboard, logs, paper, settings, strategy
from app.services_bot import bot_automation_loop
from app.services_stream import manager, market_stream_loop

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

    app.state.market_stop_event = asyncio.Event()
    app.state.market_task = asyncio.create_task(market_stream_loop(app.state.market_stop_event))

    app.state.bot_stop_event = asyncio.Event()
    app.state.bot_task = asyncio.create_task(bot_automation_loop(app.state.bot_stop_event))


@app.on_event("shutdown")
async def on_shutdown():
    stop_event = getattr(app.state, "market_stop_event", None)
    if stop_event:
        stop_event.set()
    task = getattr(app.state, "market_task", None)
    if task:
        await task

    bot_stop_event = getattr(app.state, "bot_stop_event", None)
    if bot_stop_event:
        bot_stop_event.set()
    bot_task = getattr(app.state, "bot_task", None)
    if bot_task:
        await bot_task


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
