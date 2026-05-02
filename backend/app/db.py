from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def apply_runtime_migrations():
    stmts = [
        "CREATE TABLE IF NOT EXISTS users (id UUID PRIMARY KEY, email VARCHAR(255) UNIQUE NOT NULL, password_hash VARCHAR(255) NOT NULL, is_active BOOLEAN NOT NULL DEFAULT TRUE, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())",
        "ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS balance NUMERIC(14,2) NOT NULL DEFAULT 10000",
        "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
        "DO $$ BEGIN CREATE TYPE trade_mode AS ENUM ('paper', 'live'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
        "ALTER TABLE IF EXISTS app_settings ADD COLUMN IF NOT EXISTS api_key VARCHAR(255)",
        "ALTER TABLE IF EXISTS app_settings ADD COLUMN IF NOT EXISTS api_secret VARCHAR(255)",
        "ALTER TABLE IF EXISTS app_settings ADD COLUMN IF NOT EXISTS exchange_name VARCHAR(50) DEFAULT 'binance'",
        "ALTER TABLE IF EXISTS app_settings ADD COLUMN IF NOT EXISTS trade_mode trade_mode DEFAULT 'paper'",
        "ALTER TABLE IF EXISTS logs ADD COLUMN IF NOT EXISTS user_id UUID",
        "DO $$ BEGIN ALTER TABLE logs ADD CONSTRAINT fk_logs_user_id FOREIGN KEY (user_id) REFERENCES users(id); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
        "CREATE INDEX IF NOT EXISTS idx_logs_user_id ON logs(user_id)",
        "ALTER TABLE IF EXISTS paper_orders ADD COLUMN IF NOT EXISTS user_id UUID",
        "DO $$ BEGIN ALTER TABLE paper_orders ADD CONSTRAINT fk_paper_orders_user_id FOREIGN KEY (user_id) REFERENCES users(id); EXCEPTION WHEN duplicate_object THEN NULL; END $$;",
        "CREATE INDEX IF NOT EXISTS idx_paper_orders_user_id ON paper_orders(user_id)",
        "CREATE TABLE IF NOT EXISTS user_balance (user_id UUID PRIMARY KEY REFERENCES users(id), balance NUMERIC(14,2) NOT NULL DEFAULT 10000, updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW())",
        "CREATE TABLE IF NOT EXISTS user_positions (id SERIAL PRIMARY KEY, user_id UUID NOT NULL REFERENCES users(id), asset VARCHAR(20) NOT NULL, quantity NUMERIC(14,4) NOT NULL DEFAULT 0, updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), CONSTRAINT uq_user_positions_user_asset UNIQUE(user_id, asset))",
        "CREATE INDEX IF NOT EXISTS idx_user_positions_user_id ON user_positions(user_id)",
        "ALTER TABLE IF EXISTS user_positions ADD COLUMN IF NOT EXISTS avg_entry_price NUMERIC(14,4) NOT NULL DEFAULT 0",
        "ALTER TABLE IF EXISTS app_settings ADD COLUMN IF NOT EXISTS simulated_balance NUMERIC(14,2) NOT NULL DEFAULT 10000",
        "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"",
        # C2: widen columns to fit Fernet ciphertext
        "ALTER TABLE IF EXISTS app_settings ALTER COLUMN api_key TYPE VARCHAR(512)",
        "ALTER TABLE IF EXISTS app_settings ALTER COLUMN api_secret TYPE VARCHAR(512)",
    ]

    for stmt in stmts:
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
        except Exception as exc:
            # Keep startup resilient if one optional migration fails on managed PG.
            print(f"migration warning: {exc}")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
