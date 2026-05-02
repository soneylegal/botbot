import os
import sys

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/swingbot",
)
API_TITLE = os.getenv("API_TITLE", "Swing Trade Bot API")
API_VERSION = os.getenv("API_VERSION", "0.1.0")

# ---------------------------------------------------------------------------
# Security: JWT  (C4 — obrigatório, sem default inseguro)
# ---------------------------------------------------------------------------
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
if not JWT_SECRET_KEY or JWT_SECRET_KEY == "change-me-in-production":
    print(
        "FATAL: JWT_SECRET_KEY must be set to a strong, unique secret.\n"
        "       Generate one with:  python -c \"import secrets; print(secrets.token_urlsafe(64))\"",
        file=sys.stderr,
    )
    sys.exit(1)

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "120"))
JWT_REFRESH_EXPIRE_MINUTES = int(os.getenv("JWT_REFRESH_EXPIRE_MINUTES", "10080"))

# ---------------------------------------------------------------------------
# Security: Field-level encryption for API keys at rest  (C2)
# ---------------------------------------------------------------------------
FIELD_ENCRYPTION_KEY = os.getenv("FIELD_ENCRYPTION_KEY", "")
if not FIELD_ENCRYPTION_KEY:
    print(
        "FATAL: FIELD_ENCRYPTION_KEY must be set (Fernet base64 key).\n"
        '       Generate one with:  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"',
        file=sys.stderr,
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# CORS  (C8 — origens restritas, sem wildcard)
# ---------------------------------------------------------------------------
_raw_origins = os.getenv("CORS_ORIGINS", "http://localhost:8081,http://localhost:19006")
CORS_ORIGINS: list[str] = [o.strip() for o in _raw_origins.split(",") if o.strip()]

# ---------------------------------------------------------------------------
# Intervals
# ---------------------------------------------------------------------------
MARKET_STREAM_INTERVAL_SECONDS = float(os.getenv("MARKET_STREAM_INTERVAL_SECONDS", "2.0"))
BOT_AUTOMATION_INTERVAL_SECONDS = float(os.getenv("BOT_AUTOMATION_INTERVAL_SECONDS", "60.0"))
