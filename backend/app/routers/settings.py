from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.crud import get_or_create_settings, test_exchange_connection, update_settings
from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import SettingsIn, SettingsOut

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("", response_model=SettingsOut)
def get_settings(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    item = get_or_create_settings(db)
    return SettingsOut(
        api_key_masked=item.api_key_masked,
        api_secret_masked=item.api_secret_masked,
        exchange_name=item.exchange_name or "binance",
        trade_mode=item.trade_mode,
        paper_trading=item.paper_trading,
        dark_mode=item.dark_mode,
        simulated_balance=float(item.simulated_balance),
        updated_at=item.updated_at,
    )


@router.put("", response_model=SettingsOut)
def save_settings(payload: SettingsIn, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    item = update_settings(db, payload, user_id=_.id)
    return SettingsOut(
        api_key_masked=item.api_key_masked,
        api_secret_masked=item.api_secret_masked,
        exchange_name=item.exchange_name or "binance",
        trade_mode=item.trade_mode,
        paper_trading=item.paper_trading,
        dark_mode=item.dark_mode,
        simulated_balance=float(item.simulated_balance),
        updated_at=item.updated_at,
    )


@router.post("/test-connection")
def test_exchange_connection_route(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    ok, message = test_exchange_connection(db, user_id=_.id)
    return {"ok": ok, "message": message}
