from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.crud import get_dashboard_data
from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import DashboardResponse

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardResponse)
def get_dashboard(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return get_dashboard_data(db)
