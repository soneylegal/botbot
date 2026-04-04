-- PostgreSQL schema for Swing Trade Bot

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TYPE log_level AS ENUM ('success', 'error', 'info', 'warning');
CREATE TYPE order_side AS ENUM ('buy', 'sell');
CREATE TYPE order_status AS ENUM ('filled', 'cancelled', 'pending');
CREATE TYPE trade_mode AS ENUM ('paper', 'live');

CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

CREATE TABLE IF NOT EXISTS strategy_configs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  asset VARCHAR(20) NOT NULL,
  timeframe VARCHAR(10) NOT NULL,
  ma_short_period INTEGER NOT NULL CHECK (ma_short_period > 0),
  ma_long_period INTEGER NOT NULL CHECK (ma_long_period > ma_short_period),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bot_status (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  status VARCHAR(20) NOT NULL,
  daily_pnl NUMERIC(14,2) NOT NULL DEFAULT 0,
  current_asset VARCHAR(20),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS market_ticks (
  id BIGSERIAL PRIMARY KEY,
  asset VARCHAR(20) NOT NULL,
  price NUMERIC(14,4) NOT NULL,
  volume NUMERIC(20,4) DEFAULT 0,
  tick_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_market_ticks_asset_time ON market_ticks(asset, tick_at DESC);

CREATE TABLE IF NOT EXISTS backtest_results (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  strategy_config_id UUID REFERENCES strategy_configs(id) ON DELETE SET NULL,
  period_label VARCHAR(20) NOT NULL,
  total_return NUMERIC(8,2) NOT NULL,
  win_rate NUMERIC(6,2) NOT NULL,
  max_drawdown NUMERIC(8,2) NOT NULL,
  sharpe_ratio NUMERIC(8,2) NOT NULL,
  equity_curve JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS logs (
  id BIGSERIAL PRIMARY KEY,
  level log_level NOT NULL,
  message TEXT NOT NULL,
  details JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS app_settings (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  api_key_masked VARCHAR(255),
  api_secret_masked VARCHAR(255),
  api_key VARCHAR(255),
  api_secret VARCHAR(255),
  exchange_name VARCHAR(50) NOT NULL DEFAULT 'binance',
  trade_mode trade_mode NOT NULL DEFAULT 'paper',
  paper_trading BOOLEAN NOT NULL DEFAULT TRUE,
  dark_mode BOOLEAN NOT NULL DEFAULT TRUE,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS paper_account (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  balance NUMERIC(14,2) NOT NULL DEFAULT 10000,
  open_position_asset VARCHAR(20),
  open_position_qty NUMERIC(14,4) NOT NULL DEFAULT 0,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS paper_orders (
  id BIGSERIAL PRIMARY KEY,
  side order_side NOT NULL,
  asset VARCHAR(20) NOT NULL,
  price NUMERIC(14,4) NOT NULL,
  quantity NUMERIC(14,4) NOT NULL,
  status order_status NOT NULL DEFAULT 'filled',
  simulated BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed inicial
INSERT INTO strategy_configs (asset, timeframe, ma_short_period, ma_long_period)
SELECT 'PETR4', '5M', 9, 21
WHERE NOT EXISTS (SELECT 1 FROM strategy_configs);

INSERT INTO bot_status (status, daily_pnl, current_asset)
SELECT 'Running', 150.20, 'PETR4'
WHERE NOT EXISTS (SELECT 1 FROM bot_status);

INSERT INTO app_settings (api_key_masked, api_secret_masked, exchange_name, trade_mode, paper_trading, dark_mode)
SELECT '********************', '********************', 'binance', 'paper', TRUE, TRUE
WHERE NOT EXISTS (SELECT 1 FROM app_settings);

INSERT INTO paper_account (balance, open_position_asset, open_position_qty)
SELECT 10000, 'PETR4', 100
WHERE NOT EXISTS (SELECT 1 FROM paper_account);
