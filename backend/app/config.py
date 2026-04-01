import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/swingbot",
)
API_TITLE = os.getenv("API_TITLE", "Swing Trade Bot API")
API_VERSION = os.getenv("API_VERSION", "0.1.0")
