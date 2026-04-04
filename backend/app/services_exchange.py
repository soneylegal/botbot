from __future__ import annotations

import ccxt
from datetime import datetime, timedelta, timezone
import importlib
import time
import math

yf = None
try:  # pragma: no cover - optional dependency at runtime
    yf = importlib.import_module("yfinance")
except Exception:
    yf = None

from app import models
from app.asset_universe import CRYPTO_TOP10


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
                return yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
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
        values = []
        if hasattr(close_col, "values"):
            try:
                values = close_col.values.flatten().tolist()
            except Exception:
                values = []

        cleaned = []
        for v in values:
            try:
                n = float(v)
                if math.isfinite(n) and n > 0:
                    cleaned.append(n)
            except Exception:
                continue

        idx = [t.to_pydatetime().replace(tzinfo=timezone.utc) for t in df.index]
        if not cleaned or len(cleaned) != len(idx):
            return [], []
        return cleaned, idx

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
        now = datetime.now(timezone.utc)
        since = int((now - timedelta(days=days)).timestamp() * 1000)

        if asset in {"BTC", "ETH", "SOL", "BNB", "ADA", "XRP"}:
            symbol = f"{asset}/USDT"
            try:
                client = self._build_public_client()
                candles = client.fetch_ohlcv(symbol, timeframe="1h", since=since, limit=min(1500, days * 24 + 48))
                prices = [float(c[4]) for c in candles if c and c[4] is not None]
                times = [datetime.fromtimestamp(c[0] / 1000, tz=timezone.utc) for c in candles if c and c[0] is not None]
                if prices and len(prices) == len(times):
                    return prices, times
            except Exception:
                pass

        ticker = self._to_yfinance_ticker(asset)
        if self._is_crypto_asset(asset):
            fallback_matrix: list[tuple[str, str]] = [
                (f"{days}d", "1h"),
                (f"{max(days, 5)}d", "1d"),
                ("1y", "1d"),
            ]
        else:
            fallback_matrix = [
                (f"{days}d", "1h" if days <= 60 else "1d"),
                (f"{days}d", "1d"),
            ]

        for period, interval in fallback_matrix:
            df = self._download_yf_close(ticker, period=period, interval=interval)
            if df is None or df.empty or "Close" not in df:
                continue
            closes, idx = self._extract_close_values(df)
            if closes and len(closes) == len(idx):
                return closes, idx

        return [], []

    def fetch_spot_price(self, asset: str, cache_ttl_seconds: int = 60) -> float | None:
        asset = asset.upper()
        now_ts = time.time()

        cached = self._spot_cache.get(asset)
        if cached and (now_ts - cached[1]) < cache_ttl_seconds:
            return cached[0]

        price: float | None = None

        if asset in {"BTC", "ETH", "SOL", "BNB", "ADA", "XRP"}:
            try:
                client = self._build_public_client()
                ticker = client.fetch_ticker(f"{asset}/USDT")
                p = float(ticker.get("last") or ticker.get("close") or 0)
                if p > 0:
                    price = p
            except Exception:
                price = None

        if price is None:
            ticker = self._to_yfinance_ticker(asset)
            hist = self._download_yf_close(ticker, period="1d", interval="1m")
            if hist is None or hist.empty or "Close" not in hist:
                # fallback para fechamento anterior quando intraday faltar/rate limit
                hist = self._download_yf_close(ticker, period="5d", interval="1d")
            if hist is not None and not hist.empty and "Close" in hist:
                closes, _ = self._extract_close_values(hist)
                if closes:
                    p = float(closes[-1])
                    if math.isfinite(p) and p > 0:
                        price = p

        if price is not None and math.isfinite(price) and price > 0:
            self._spot_cache[asset] = (price, now_ts)
            return price

        return None
