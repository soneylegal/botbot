from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.asset_universe import ALL_ASSETS, B3_TOP20, CRYPTO_TOP10
from app.crud import get_latest_backtest, run_backtest
from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import AssetUniverseOut, BacktestResponse, BacktestRunIn

router = APIRouter(prefix="/backtest", tags=["Backtest"])


@router.get("/assets", response_model=AssetUniverseOut)
def get_backtest_assets(_: User = Depends(get_current_user)):
    return AssetUniverseOut(b3=B3_TOP20, crypto=CRYPTO_TOP10, all=ALL_ASSETS)


@router.get("/results", response_model=BacktestResponse)
def get_backtest_results(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return get_latest_backtest(db)


@router.post("/run", response_model=BacktestResponse)
def run_backtest_route(
    payload: BacktestRunIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.asset and payload.asset.upper() not in ALL_ASSETS:
        raise HTTPException(status_code=400, detail="Ativo inválido para backtest")

    return run_backtest(db, payload.period_label, user_id=current_user.id, asset=payload.asset)
