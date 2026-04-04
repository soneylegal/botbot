from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import os

import jwt

from app.config import JWT_ALGORITHM, JWT_EXPIRE_MINUTES, JWT_REFRESH_EXPIRE_MINUTES, JWT_SECRET_KEY

def hash_password(password: str) -> str:
    salt = os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 120_000).hex()
    return f"pbkdf2_sha256${salt}${digest}"


def verify_password(password: str, hashed_password: str) -> bool:
    # Compatibilidade com hash legado pbkdf2_sha256$salt$digest
    if hashed_password.startswith("pbkdf2_sha256$"):
        try:
            _, salt, stored = hashed_password.split("$", 2)
            digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 120_000).hex()
            return hmac.compare_digest(digest, stored)
        except Exception:
            return False

    return False


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_REFRESH_EXPIRE_MINUTES)
    payload = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
