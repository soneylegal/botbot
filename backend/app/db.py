from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def apply_runtime_migrations():
    stmts = [
        "DO $$ BEGIN CREATE TYPE trade_mode AS ENUM ('paper', 'live'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
        "ALTER TABLE IF EXISTS app_settings ADD COLUMN IF NOT EXISTS api_key VARCHAR(255)",
        "ALTER TABLE IF EXISTS app_settings ADD COLUMN IF NOT EXISTS api_secret VARCHAR(255)",
        "ALTER TABLE IF EXISTS app_settings ADD COLUMN IF NOT EXISTS exchange_name VARCHAR(50) DEFAULT 'binance'",
        "ALTER TABLE IF EXISTS app_settings ADD COLUMN IF NOT EXISTS trade_mode trade_mode DEFAULT 'paper'",
        "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"",
        "CREATE TABLE IF NOT EXISTS users (id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), email VARCHAR(255) UNIQUE NOT NULL, password_hash VARCHAR(255) NOT NULL, is_active BOOLEAN NOT NULL DEFAULT TRUE, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())",
        "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
    ]

    with engine.begin() as conn:
        for stmt in stmts:
            conn.execute(text(stmt))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
