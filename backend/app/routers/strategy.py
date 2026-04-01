from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.crud import get_or_create_strategy, upsert_strategy
from app.db import get_db
from app.schemas import StrategyConfigIn, StrategyConfigOut

router = APIRouter(prefix="/strategy", tags=["Strategy"])


@router.get("/config", response_model=StrategyConfigOut)
def get_strategy_config(db: Session = Depends(get_db)):
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
def update_strategy_config(payload: StrategyConfigIn, db: Session = Depends(get_db)):
    if payload.ma_long_period <= payload.ma_short_period:
        raise HTTPException(status_code=400, detail="MA long deve ser maior que MA short")

    item = upsert_strategy(db, payload)
    return StrategyConfigOut(
        id=str(item.id),
        asset=item.asset,
        timeframe=item.timeframe,
        ma_short_period=item.ma_short_period,
        ma_long_period=item.ma_long_period,
        updated_at=item.updated_at,
    )
