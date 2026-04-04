from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.crud import get_latest_backtest, run_backtest
from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import BacktestResponse, BacktestRunIn

router = APIRouter(prefix="/backtest", tags=["Backtest"])


@router.get("/results", response_model=BacktestResponse)
def get_backtest_results(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return get_latest_backtest(db)


@router.post("/run", response_model=BacktestResponse)
def run_backtest_route(
    payload: BacktestRunIn,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return run_backtest(db, payload.period_label)
