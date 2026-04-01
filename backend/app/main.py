from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import API_TITLE, API_VERSION
from app.db import Base, engine
from app.routers import backtest, dashboard, logs, paper, settings, strategy

app = FastAPI(title=API_TITLE, version=API_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"ok": True}


app.include_router(dashboard.router)
app.include_router(strategy.router)
app.include_router(backtest.router)
app.include_router(logs.router)
app.include_router(settings.router)
app.include_router(paper.router)
