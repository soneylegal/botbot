from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.crud import get_or_create_settings, update_settings
from app.db import get_db
from app.schemas import SettingsIn, SettingsOut

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("", response_model=SettingsOut)
def get_settings(db: Session = Depends(get_db)):
    item = get_or_create_settings(db)
    return SettingsOut(
        api_key_masked=item.api_key_masked,
        api_secret_masked=item.api_secret_masked,
        paper_trading=item.paper_trading,
        dark_mode=item.dark_mode,
        updated_at=item.updated_at,
    )


@router.put("", response_model=SettingsOut)
def save_settings(payload: SettingsIn, db: Session = Depends(get_db)):
    item = update_settings(db, payload)
    return SettingsOut(
        api_key_masked=item.api_key_masked,
        api_secret_masked=item.api_secret_masked,
        paper_trading=item.paper_trading,
        dark_mode=item.dark_mode,
        updated_at=item.updated_at,
    )


@router.post("/test-connection")
def test_exchange_connection():
    # Stub inicial: no próximo passo integrar SDK da corretora.
    return {"ok": True, "message": "Conexão testada com sucesso (simulado)."}
