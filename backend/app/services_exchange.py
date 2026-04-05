from __future__ import annotations

import ccxt
from datetime import datetime, timezone
import importlib
import time
import math

requests = None
try:  # pragma: no cover - optional dependency at runtime
    requests = importlib.import_module("requests")
except Exception:
    requests = None

yf = None
try:  # pragma: no cover - optional dependency at runtime
    yf = importlib.import_module("yfinance")
except Exception:
    yf = None

from app import models
from app.asset_universe import CRYPTO_TOP10
from sqlalchemy.orm import Session

YF_SESSION = None
if requests is not None:
    try:
        YF_SESSION = requests.Session()
        YF_SESSION.headers.update({"User-Agent": "Mozilla/5.0 Windows NT 10.0"})
    except Exception:
        YF_SESSION = None


class ExchangeService:
    _spot_cache: dict[str, tuple[float, float]] = {}

    @classmethod
    def clear_spot_cache(cls, asset: str | None = None):
        if asset is None:
            cls._spot_cache.clear()
            return
        cls._spot_cache.pop(asset.upper(), None)

    def __init__(self, settings: models.AppSettings):
        self.settings = settings

    @property
    def is_live(self) -> bool:
        return self.settings.trade_mode == models.TradeMode.live and bool(self.settings.api_key and self.settings.api_secret)

    def _build_client(self):
        exchange_name = (self.settings.exchange_name or "binance").lower()
        exchange_cls = getattr(ccxt, exchange_name, ccxt.binance)
        return exchange_cls(
            {
                "apiKey": self.settings.api_key,
                "secret": self.settings.api_secret,
                "enableRateLimit": True,
            }
        )

    def _build_public_client(self):
        exchange_name = (self.settings.exchange_name or "binance").lower()
        exchange_cls = getattr(ccxt, exchange_name, ccxt.binance)
        return exchange_cls({"enableRateLimit": True})

    @staticmethod
    def _is_crypto_asset(asset: str) -> bool:
        return asset.upper() in set(CRYPTO_TOP10)

    def _to_yfinance_ticker(self, asset: str) -> str:
        asset = asset.upper()
        if self._is_crypto_asset(asset):
            return f"{asset}-USD"
        return f"{asset}.SA"

    def _download_yf_close(self, ticker: str, period: str, interval: str):
        if yf is None:
            return None
        last_error = None
        for attempt in range(3):
            try:
                return yf.download(
                    ticker,
                    period=period,
                    interval=interval,
                    progress=False,
                    auto_adjust=False,
                    session=YF_SESSION,
                )
            except Exception as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(0.4 * (attempt + 1))
        _ = last_error
        return None

    @staticmethod
    def _extract_close_values(df):
        if df is None or getattr(df, "empty", True):
            return [], []

        if "Close" not in df:
            return [], []

        close_col = df["Close"]
        values: list[float] = []
        try:
            # Series path
            values = close_col.values.tolist()
        except Exception:
            try:
                # DataFrame (single-column) path
                values = close_col.values.flatten().tolist()
            except Exception:
                values = []

        idx = [t.to_pydatetime().replace(tzinfo=timezone.utc) for t in df.index]
        if not values or not idx:
            return [], []

        cleaned: list[float] = []
        cleaned_idx: list[datetime] = []
        for raw_v, raw_t in zip(values, idx):
            try:
                n = float(raw_v)
                if math.isfinite(n) and n > 0:
                    cleaned.append(n)
                    cleaned_idx.append(raw_t)
            except Exception:
                continue

        if not cleaned:
            return [], []
        return cleaned, cleaned_idx

    def fetch_last_price(self, symbol: str) -> float | None:
        if not self.is_live:
            return None
        try:
            client = self._build_client()
            ticker = client.fetch_ticker(symbol)
            return float(ticker.get("last") or ticker.get("close") or 0)
        except Exception:
            return None

    def create_live_order(self, symbol: str, side: str, amount: float, price: float | None = None) -> dict:
        client = self._build_client()
        order_side = "buy" if side.lower() == "buy" else "sell"
        if price and price > 0:
            return client.create_limit_order(symbol, order_side, amount, price)
        return client.create_market_order(symbol, order_side, amount)

    def fetch_historical_closes(self, asset: str, days: int) -> tuple[list[float], list[datetime]]:
        asset = asset.upper()
        symbol = self._to_yfinance_ticker(asset)
        period = f"{max(int(days), 1)}d"

        def _is_valid_series(prices: list[float], times: list[datetime]) -> bool:
            return len(prices) >= 2 and len(times) >= 2 and len(prices) == len(times)

        if yf is not None:
            try:
                df = self._download_yf_close(symbol, period=period, interval="1d")
                prices, times = self._extract_close_values(df)
                if _is_valid_series(prices, times):
                    return prices, times
            except Exception:
                pass

            try:
                ticker = yf.Ticker(symbol, session=YF_SESSION)
                df = ticker.history(period=period, interval="1d", auto_adjust=False)
                prices, times = self._extract_close_values(df)
                if _is_valid_series(prices, times):
                    return prices, times
            except Exception:
                pass

        if yf is not None:
            try:
                fallback_period = "1y" if not self._is_crypto_asset(asset) else "6mo"
                df = self._download_yf_close(symbol, period=fallback_period, interval="1d")
                prices, times = self._extract_close_values(df)
                if _is_valid_series(prices, times):
                    return prices, times
            except Exception:
                pass

        if self._is_crypto_asset(asset):
            try:
                client = self._build_public_client()
                timeframe = "1h" if days <= 60 else "1d"
                limit = max(200, min(1000, int(days * (24 if timeframe == "1h" else 1)) + 20))
                candles = client.fetch_ohlcv(f"{asset}/USDT", timeframe=timeframe, limit=limit)
                prices = [float(c[4]) for c in candles if c and c[4] is not None and float(c[4]) > 0]
                times = [datetime.fromtimestamp(c[0] / 1000, tz=timezone.utc) for c in candles if c and c[0] is not None]
                if _is_valid_series(prices, times):
                    return prices, times
            except Exception:
                pass

            raise ValueError(f"Sem dados históricos suficientes para {asset}")

    def fetch_spot_price(self, asset: str, cache_ttl_seconds: int = 60, db: Session | None = None) -> float | None:
        asset = asset.upper()
        if yf is None:
            if db is not None:
                last = (
                    db.query(models.MarketTick)
                    .filter(models.MarketTick.asset == asset)
                    .order_by(models.MarketTick.tick_at.desc())
                    .first()
                )
                if last and float(last.price) > 0:
                    return float(last.price)
            return None

        symbol = self._to_yfinance_ticker(asset)
        ticker = yf.Ticker(symbol, session=YF_SESSION)

        try:
            price = float(ticker.fast_info["lastPrice"])
            if math.isfinite(price) and price > 0:
                return price
        except Exception:
            pass

        try:
            hist = ticker.history(period="1d", interval="1m", auto_adjust=False)
            if hist is not None and not hist.empty:
                close = float(hist["Close"].dropna().iloc[-1])
                if math.isfinite(close) and close > 0:
                    return close
        except Exception:
            pass

        if db is not None:
            last = (
                db.query(models.MarketTick)
                .filter(models.MarketTick.asset == asset)
                .order_by(models.MarketTick.tick_at.desc())
                .first()
            )
            if last and float(last.price) > 0:
                return float(last.price)

        return None
