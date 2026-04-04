from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import models
from app.crud import close_open_position, create_live_or_paper_order, get_paper_state, reset_paper_wallet
from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import PaperOrderIn, PaperOrderOut, PaperStateResponse

router = APIRouter(prefix="/paper", tags=["Paper Trading"])


@router.get("/state", response_model=PaperStateResponse)
def get_state(
    asset: str | None = Query(None, description="Ativo de foco para preço/PnL"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return get_paper_state(db, user_id=_.id, focus_asset=asset)


@router.post("/buy", response_model=PaperOrderOut)
def buy(payload: PaperOrderIn, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    try:
        order = create_live_or_paper_order(db, models.OrderSide.buy, payload, user_id=_.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Serviço de cotações temporariamente indisponível. Tente novamente em instantes.",
        ) from exc
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
def sell(payload: PaperOrderIn, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    try:
        order = create_live_or_paper_order(db, models.OrderSide.sell, payload, user_id=_.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Serviço de cotações temporariamente indisponível. Tente novamente em instantes.",
        ) from exc
    return PaperOrderOut(
        id=order.id,
        side=order.side.value,
        asset=order.asset,
        price=float(order.price),
        quantity=float(order.quantity),
        status=order.status.value,
        created_at=order.created_at,
    )


@router.post("/close", response_model=PaperOrderOut)
def close_position(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    try:
        order = close_open_position(db, user_id=_.id)
    except ValueError as exc:
        message = str(exc)
        if "preço atual" in message.lower() or "cota" in message.lower() or "rate limit" in message.lower():
            raise HTTPException(
                status_code=503,
                detail="Serviço de cotações temporariamente indisponível. Tente novamente em instantes.",
            ) from exc
        raise HTTPException(status_code=400, detail=message) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Serviço de cotações temporariamente indisponível. Tente novamente em instantes.",
        ) from exc
    return PaperOrderOut(
        id=order.id,
        side=order.side.value,
        asset=order.asset,
        price=float(order.price),
        quantity=float(order.quantity),
        status=order.status.value,
        created_at=order.created_at,
    )


@router.post("/reset", response_model=PaperStateResponse)
def reset_wallet(
    initial_balance: float | None = Query(None, gt=0, description="Saldo inicial customizado para reset da carteira"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    try:
        return reset_paper_wallet(db, user_id=_.id, initial_balance=(initial_balance or 10000.0))
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Não foi possível resetar a carteira paper.") from exc
