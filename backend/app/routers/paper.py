from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models
from app.crud import create_paper_order, get_paper_state
from app.db import get_db
from app.schemas import PaperOrderIn, PaperOrderOut, PaperStateResponse

router = APIRouter(prefix="/paper", tags=["Paper Trading"])


@router.get("/state", response_model=PaperStateResponse)
def get_state(db: Session = Depends(get_db)):
    return get_paper_state(db)


@router.post("/buy", response_model=PaperOrderOut)
def buy(payload: PaperOrderIn, db: Session = Depends(get_db)):
    order = create_paper_order(db, models.OrderSide.buy, payload)
    return PaperOrderOut(
        id=order.id,
        side=order.side.value,
        asset=order.asset,
        price=float(order.price),
        quantity=float(order.quantity),
        status=order.status.value,
        created_at=order.created_at,
    )


@router.post("/sell", response_model=PaperOrderOut)
def sell(payload: PaperOrderIn, db: Session = Depends(get_db)):
    order = create_paper_order(db, models.OrderSide.sell, payload)
    return PaperOrderOut(
        id=order.id,
        side=order.side.value,
        asset=order.asset,
        price=float(order.price),
        quantity=float(order.quantity),
        status=order.status.value,
        created_at=order.created_at,
    )
