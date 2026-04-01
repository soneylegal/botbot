from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.crud import get_latest_backtest
from app.db import get_db
from app.schemas import BacktestResponse

router = APIRouter(prefix="/backtest", tags=["Backtest"])


@router.get("/results", response_model=BacktestResponse)
def get_backtest_results(db: Session = Depends(get_db)):
    return get_latest_backtest(db)


@router.post("/run", response_model=BacktestResponse)
def run_backtest(db: Session = Depends(get_db)):
    # Stub inicial: retorna/gera resultado mock persistido.
    return get_latest_backtest(db)
