import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.asset_universe import ALL_ASSETS, B3_TOP20, CRYPTO_TOP10
from app.core_unified import get_or_create_strategy, upsert_strategy
from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import AssetUniverseOut, StrategyConfigIn, StrategyConfigOut

router = APIRouter(prefix="/strategy", tags=["Strategy"])
logger = logging.getLogger(__name__)


@router.get("/assets", response_model=AssetUniverseOut)
def get_strategy_assets(_: User = Depends(get_current_user)):
    try:
        return AssetUniverseOut(b3=B3_TOP20, crypto=CRYPTO_TOP10, all=ALL_ASSETS)
    except Exception as e:
        logger.error(f"Erro na rota: {e}")
        raise HTTPException(status_code=500, detail={"message": "Falha ao listar ativos", "fallback": []}) from e


@router.get("/config", response_model=StrategyConfigOut)
def get_strategy_config(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    item = get_or_create_strategy(db)
    return StrategyConfigOut(
        id=str(item.id),
        asset=item.asset,
        timeframe=item.timeframe,
        ma_short_period=item.ma_short_period,
        ma_long_period=item.ma_long_period,
        updated_at=item.updated_at,
    )


@router.put("/config", response_model=StrategyConfigOut)
def update_strategy_config(
    payload: StrategyConfigIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.asset.upper() not in ALL_ASSETS:
        raise HTTPException(status_code=400, detail="Ativo inválido para estratégia")

    if payload.ma_long_period <= payload.ma_short_period:
        raise HTTPException(status_code=400, detail="MA long deve ser maior que MA short")

    item = upsert_strategy(db, payload, user_id=current_user.id)
    return StrategyConfigOut(
        id=str(item.id),
        asset=item.asset,
        timeframe=item.timeframe,
        ma_short_period=item.ma_short_period,
        ma_long_period=item.ma_long_period,
        updated_at=item.updated_at,
    )
