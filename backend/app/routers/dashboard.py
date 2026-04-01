from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.crud import get_dashboard_data
from app.db import get_db
from app.schemas import DashboardResponse

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardResponse)
def get_dashboard(db: Session = Depends(get_db)):
    return get_dashboard_data(db)
