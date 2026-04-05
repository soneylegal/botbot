import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.crud import create_log, list_logs
from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import LogIn, LogOut

router = APIRouter(prefix="/logs", tags=["Logs"])
logger = logging.getLogger(__name__)


@router.get("", response_model=list[LogOut])
def get_logs(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        items = list_logs(db, user_id=current_user.id, limit=limit)
        return [
            LogOut(
                id=i.id,
                user_id=(str(i.user_id) if i.user_id else None),
                level=i.level.value,
                message=i.message,
                details=i.details,
                created_at=i.created_at,
            )
            for i in items
        ]
    except Exception as e:
        logger.error(f"Erro na rota: {e}")
        raise HTTPException(status_code=500, detail={"message": "Falha ao listar logs", "fallback": []}) from e


@router.post("", response_model=LogOut)
def add_log(payload: LogIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    item = create_log(db, payload, user_id=current_user.id)
    return LogOut(
        id=item.id,
        user_id=(str(item.user_id) if item.user_id else None),
        level=item.level.value,
        message=item.message,
        details=item.details,
        created_at=item.created_at,
    )
