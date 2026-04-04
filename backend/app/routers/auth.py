from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud import authenticate_user, create_user, get_user_by_email
from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import AuthLoginIn, AuthRegisterIn, RefreshTokenIn, TokenOut, UserOut
from app.security import create_access_token, create_refresh_token, decode_access_token

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserOut)
def register(payload: AuthRegisterIn, db: Session = Depends(get_db)):
    if get_user_by_email(db, payload.email):
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    user = create_user(db, payload.email, payload.password)
    return UserOut(id=str(user.id), email=user.email)


@router.post("/login", response_model=TokenOut)
def login(payload: AuthLoginIn, db: Session = Depends(get_db)):
    user = authenticate_user(db, payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
    return TokenOut(
        access_token=create_access_token(user.email),
        refresh_token=create_refresh_token(user.email),
    )


@router.post("/refresh", response_model=TokenOut)
def refresh(payload: RefreshTokenIn, db: Session = Depends(get_db)):
    try:
        decoded = decode_access_token(payload.refresh_token)
        if decoded.get("type") != "refresh":
            raise ValueError("invalid refresh type")
        email = decoded.get("sub")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token inválido") from exc

    user = get_user_by_email(db, email or "")
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado")

    return TokenOut(
        access_token=create_access_token(user.email),
        refresh_token=create_refresh_token(user.email),
    )


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return UserOut(id=str(current_user.id), email=current_user.email)
