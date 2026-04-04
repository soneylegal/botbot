from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.crud import create_log, list_logs
from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import LogIn, LogOut

router = APIRouter(prefix="/logs", tags=["Logs"])


@router.get("", response_model=list[LogOut])
def get_logs(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    items = list_logs(db, limit)
    return [
        LogOut(id=i.id, level=i.level.value, message=i.message, details=i.details, created_at=i.created_at)
        for i in items
    ]


@router.post("", response_model=LogOut)
def add_log(payload: LogIn, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    item = create_log(db, payload)
    return LogOut(
        id=item.id,
        level=item.level.value,
        message=item.message,
        details=item.details,
        created_at=item.created_at,
    )
