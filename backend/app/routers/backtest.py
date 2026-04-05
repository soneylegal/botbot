import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.asset_universe import ALL_ASSETS, B3_TOP20, CRYPTO_TOP10
from app.crud import get_latest_backtest, run_backtest
from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import AssetUniverseOut, BacktestResponse, BacktestRunIn

router = APIRouter(prefix="/backtest", tags=["Backtest"])
logger = logging.getLogger(__name__)


@router.get("/assets", response_model=AssetUniverseOut)
def get_backtest_assets(_: User = Depends(get_current_user)):
    return AssetUniverseOut(b3=B3_TOP20, crypto=CRYPTO_TOP10, all=ALL_ASSETS)


@router.get("/results", response_model=BacktestResponse)
def get_backtest_results(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    try:
        return get_latest_backtest(db)
    except Exception as e:
        logger.error(f"Erro na rota: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Falha ao obter resultados de backtest",
                "fallback": {
                    "period_label": "Error",
                    "metrics": {
                        "total_return": 0.0,
                        "win_rate": 0.0,
                        "max_drawdown": 0.0,
                        "sharpe_ratio": 0.0,
                    },
                    "equity_curve": [],
                },
            },
        ) from e


@router.post("/run", response_model=BacktestResponse)
def run_backtest_route(
    payload: BacktestRunIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.asset and payload.asset.upper() not in ALL_ASSETS:
        raise HTTPException(status_code=400, detail="Ativo inválido para backtest")
    try:
        return run_backtest(db, payload.period_label, user_id=current_user.id, asset=payload.asset)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
