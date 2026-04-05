import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core2 import get_dashboard_data
from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import DashboardResponse

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
logger = logging.getLogger(__name__)


@router.get("", response_model=DashboardResponse)
def get_dashboard(
    include_chart: bool = Query(True, description="Quando false, retorna payload leve para polling de preço/status sem histórico completo."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return get_dashboard_data(db, user_id=current_user.id, include_chart=include_chart)
    except Exception as e:
        logger.error(f"Erro na rota: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Falha ao processar dashboard",
                "fallback": {
                    "status": "Error",
                    "daily_pnl": 0.0,
                    "asset": None,
                    "price_status": "Error",
                    "position_qty": 0.0,
                    "avg_entry_price": 0.0,
                    "chart": [],
                },
            },
        ) from e
