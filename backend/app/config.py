import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/swingbot",
)
API_TITLE = os.getenv("API_TITLE", "Swing Trade Bot API")
API_VERSION = os.getenv("API_VERSION", "0.1.0")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "120"))
JWT_REFRESH_EXPIRE_MINUTES = int(os.getenv("JWT_REFRESH_EXPIRE_MINUTES", "10080"))
MARKET_STREAM_INTERVAL_SECONDS = float(os.getenv("MARKET_STREAM_INTERVAL_SECONDS", "2.0"))
BOT_AUTOMATION_INTERVAL_SECONDS = float(os.getenv("BOT_AUTOMATION_INTERVAL_SECONDS", "60.0"))
