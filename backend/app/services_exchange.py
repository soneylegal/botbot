from __future__ import annotations

import ccxt
from datetime import datetime, timedelta, timezone
import importlib
import time
import math
import logging
from typing import Any

logger = logging.getLogger(__name__)

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
    _history_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}

    @classmethod
    def clear_spot_cache(cls, asset: str | None = None):
        if asset is None:
            cls._spot_cache.clear()
            cls._history_cache.clear()
            return
        cls._spot_cache.pop(asset.upper(), None)
        cls._history_cache.pop(asset.upper(), None)

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

    @staticmethod
    def _to_ccxt_timeframe(timeframe: str | None) -> str:
        raw = (timeframe or "5m").strip().lower()
        aliases = {
            "1m": "1m",
            "5m": "5m",
            "15m": "15m",
            "30m": "30m",
            "1h": "1h",
            "4h": "4h",
            "1d": "1d",
            "1mth": "1M",
            "1m_": "1m",
            "5m_": "5m",
            "1mim": "1m",
            "1min": "1m",
            "5min": "5m",
        }
        normalized = raw.replace(" ", "")
        if normalized in {"1m", "5m", "15m", "30m", "1h", "4h", "1d"}:
            return normalized
        if normalized in {"1m", "5m", "15m", "30m", "1h", "1d"}:
            return normalized
        # UI sends values like 1M, 5M, 1H, 1D
        if normalized.endswith("m") and normalized[:-1].isdigit():
            return f"{int(normalized[:-1])}m"
        if normalized.endswith("h") and normalized[:-1].isdigit():
            return f"{int(normalized[:-1])}h"
        if normalized.endswith("d") and normalized[:-1].isdigit():
            return f"{int(normalized[:-1])}d"
        return aliases.get(normalized, "5m")

    @staticmethod
    def _to_yf_interval(timeframe: str | None) -> str:
        tf = ExchangeService._to_ccxt_timeframe(timeframe)
        mapping = {
            "1m": "1m",
            "5m": "5m",
            "15m": "15m",
            "30m": "30m",
            "1h": "60m",
            "4h": "60m",
            "1d": "1d",
        }
        return mapping.get(tf, "5m")

    @staticmethod
    def _to_brapi_interval(timeframe: str | None) -> str:
        tf = ExchangeService._to_ccxt_timeframe(timeframe)
        mapping = {
            "1m": "1m",
            "5m": "5m",
            "15m": "15m",
            "30m": "30m",
            "1h": "1h",
            "4h": "1h",
            "1d": "1d",
        }
        return mapping.get(tf, "5m")

    @staticmethod
    def _sanitize_candle(candle: dict[str, Any]) -> dict[str, Any] | None:
        try:
            close = float(candle.get("close") or 0)
            if not math.isfinite(close) or close <= 0:
                return None

            open_v = float(candle.get("open") or close)
            high_v = float(candle.get("high") or max(open_v, close))
            low_v = float(candle.get("low") or min(open_v, close))

            if not math.isfinite(open_v):
                open_v = close
            if not math.isfinite(high_v):
                high_v = max(open_v, close)
            if not math.isfinite(low_v):
                low_v = min(open_v, close)

            high_v = max(high_v, open_v, close)
            low_v = min(low_v, open_v, close)

            raw_time = str(candle.get("time") or "")
            ts = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
            ts = ts.astimezone(timezone.utc) if ts.tzinfo else ts.replace(tzinfo=timezone.utc)

            return {
                "time": ts.isoformat(),
                "open": float(open_v),
                "high": float(high_v),
                "low": float(low_v),
                "close": float(close),
            }
        except Exception:
            return None

    @staticmethod
    def _serialize_ohlc(
        times: list[datetime],
        opens: list[float],
        highs: list[float],
        lows: list[float],
        closes: list[float],
    ) -> list[dict[str, Any]]:
        points: list[dict[str, Any]] = []
        for t, o, h, l, c in zip(times, opens, highs, lows, closes):
            try:
                ts = t.astimezone(timezone.utc) if t.tzinfo else t.replace(tzinfo=timezone.utc)
                candle = ExchangeService._sanitize_candle(
                    {
                        "time": ts.isoformat(),
                        "open": float(o),
                        "high": float(h),
                        "low": float(l),
                        "close": float(c),
                    }
                )
                if candle:
                    points.append(candle)
            except Exception:
                continue
        points.sort(key=lambda x: str(x["time"]))
        return points

    @staticmethod
    def _ensure_min_points(points: list[dict[str, Any]], min_points: int) -> list[dict[str, Any]]:
        valid = [c for c in (ExchangeService._sanitize_candle(p) for p in points) if c]
        if len(valid) >= min_points:
            return valid
        if not valid:
            return []
        if len(valid) == 1:
            only = valid[0]
            base_time = datetime.now(timezone.utc)
            close = float(only["close"])
            return [
                {
                    "time": (base_time - timedelta(minutes=(min_points - 1 - i))).isoformat(),
                    "open": close,
                    "high": close,
                    "low": close,
                    "close": close,
                }
                for i in range(min_points)
            ]

        closes = [float(p["close"]) for p in valid]
        first_time = datetime.fromisoformat(str(valid[0]["time"]).replace("Z", "+00:00"))
        last_time = datetime.fromisoformat(str(valid[-1]["time"]).replace("Z", "+00:00"))
        total_seconds = max((last_time - first_time).total_seconds(), float(min_points - 1))

        dense: list[dict[str, Any]] = []
        src_len = len(closes)
        for i in range(min_points):
            position = (i / max(min_points - 1, 1)) * (src_len - 1)
            left = int(math.floor(position))
            right = min(left + 1, src_len - 1)
            weight = position - left
            interpolated = closes[left] * (1 - weight) + closes[right] * weight
            ts = first_time + timedelta(seconds=(total_seconds * (i / max(min_points - 1, 1))))
            open_v = closes[left]
            close_v = float(interpolated)
            high_v = max(open_v, close_v)
            low_v = min(open_v, close_v)
            dense.append(
                {
                    "time": ts.astimezone(timezone.utc).isoformat(),
                    "open": float(open_v),
                    "high": float(high_v),
                    "low": float(low_v),
                    "close": float(close_v),
                }
            )
        return dense

    def _http_get_json(self, url: str, timeout: int = 10, retries: int = 3) -> dict[str, Any] | None:
        if requests is None:
            return None
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        }
        last_error = None
        for attempt in range(retries):
            try:
                response = requests.get(url, headers=headers, timeout=timeout)
                response.raise_for_status()
                return response.json()
            except Exception as exc:
                last_error = exc
                if attempt < retries - 1:
                    time.sleep(0.35 * (attempt + 1))
        _ = last_error
        return None

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
    def _extract_ohlc_values(df):
        if df is None or getattr(df, "empty", True):
            return [], [], [], [], []

        for needed in ("Open", "High", "Low", "Close"):
            if needed not in df:
                return [], [], [], [], []

        def _as_list(col_name: str) -> list[float]:
            col = df[col_name]
            try:
                return col.values.tolist()
            except Exception:
                try:
                    return col.values.flatten().tolist()
                except Exception:
                    return []

        opens = _as_list("Open")
        highs = _as_list("High")
        lows = _as_list("Low")
        closes = _as_list("Close")

        idx = [t.to_pydatetime().replace(tzinfo=timezone.utc) for t in df.index]
        if not opens or not highs or not lows or not closes or not idx:
            return [], [], [], [], []

        clean_o: list[float] = []
        clean_h: list[float] = []
        clean_l: list[float] = []
        clean_c: list[float] = []
        clean_t: list[datetime] = []
        for raw_o, raw_h, raw_l, raw_c, raw_t in zip(opens, highs, lows, closes, idx):
            try:
                o = float(raw_o)
                h = float(raw_h)
                l = float(raw_l)
                c = float(raw_c)
                if not all(math.isfinite(v) for v in [o, h, l, c]):
                    continue
                if c <= 0:
                    continue
                h = max(h, o, c)
                l = min(l, o, c)
                clean_o.append(o)
                clean_h.append(h)
                clean_l.append(l)
                clean_c.append(c)
                clean_t.append(raw_t)
            except Exception:
                continue

        return clean_o, clean_h, clean_l, clean_c, clean_t

    @staticmethod
    def _extract_close_values(df):
        opens, highs, lows, closes, times = ExchangeService._extract_ohlc_values(df)
        _ = opens
        _ = highs
        _ = lows
        return closes, times

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
        if days <= 2:
            timeframe = "5m"
            limit = 200
        elif days <= 7:
            timeframe = "15m"
            limit = 240
        elif days <= 60:
            timeframe = "1h"
            limit = 360
        else:
            timeframe = "1d"
            limit = max(90, days)

        history = self.fetch_history(asset, timeframe=timeframe, limit=limit, min_points=30)
        if not history:
            raise ValueError(f"Sem dados históricos suficientes para {asset}")

        closes: list[float] = []
        times: list[datetime] = []
        for point in history:
            try:
                close = float(point.get("close") or 0)
                if not math.isfinite(close) or close <= 0:
                    continue
                raw_time = str(point.get("time") or "")
                ts = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
                closes.append(close)
                times.append(ts.astimezone(timezone.utc))
            except Exception:
                continue

        if len(closes) < 2 or len(closes) != len(times):
            raise ValueError(f"Sem dados históricos corretos para {asset}")
        return closes, times

    def _fetch_crypto_history(self, asset: str, timeframe: str, limit: int, min_points: int) -> list[dict[str, Any]]:
        client = self._build_public_client()
        preferred = self._to_ccxt_timeframe(timeframe)
        # Fino -> grosso para evitar "degraus"
        candidates = [preferred, "1m", "5m", "15m", "30m", "1h", "4h", "1d"]
        ordered: list[str] = []
        for tf in candidates:
            if tf not in ordered:
                ordered.append(tf)

        symbol = f"{asset}/USDT"
        for tf in ordered:
            try:
                fetch_limit = max(limit, min_points * 3)
                fetch_limit = max(fetch_limit, 60)
                fetch_limit = min(fetch_limit, 1000)
                candles = client.fetch_ohlcv(symbol, timeframe=tf, limit=fetch_limit)
                points: list[dict[str, Any]] = []
                for c in candles:
                    if not c or len(c) < 5:
                        continue
                    ts_ms = c[0]
                    open_v = c[1] if len(c) > 1 else None
                    high_v = c[2] if len(c) > 2 else None
                    low_v = c[3] if len(c) > 3 else None
                    close = c[4]
                    if ts_ms is None or close is None:
                        continue
                    ts = datetime.fromtimestamp(float(ts_ms) / 1000.0, tz=timezone.utc)
                    candle = self._sanitize_candle(
                        {
                            "time": ts.isoformat(),
                            "open": open_v,
                            "high": high_v,
                            "low": low_v,
                            "close": close,
                        }
                    )
                    if candle:
                        points.append(candle)

                points = self._ensure_min_points(points, min_points)
                if len(points) >= min_points:
                    return points[-max(limit, min_points):]
            except Exception as exc:
                logger.warning("Falha ao buscar histórico cripto %s em %s: %s", asset, tf, exc)
                continue

        return []

    def _fetch_b3_history(self, asset: str, timeframe: str, limit: int, min_points: int) -> list[dict[str, Any]]:
        symbol = self._to_yfinance_ticker(asset)
        interval = self._to_yf_interval(timeframe)
        points: list[dict[str, Any]] = []

        if yf is not None:
            try:
                df = self._download_yf_close(symbol, period="5d", interval=interval)
                opens, highs, lows, closes, times = self._extract_ohlc_values(df)
                points = self._serialize_ohlc(times, opens, highs, lows, closes)
                if len(points) >= min_points:
                    return points[-max(limit, min_points):]
            except Exception as exc:
                logger.warning("Falha histórico yfinance download para %s: %s", asset, exc)

            try:
                ticker = yf.Ticker(symbol, session=YF_SESSION)
                df = ticker.history(period="5d", interval=interval, auto_adjust=False)
                opens, highs, lows, closes, times = self._extract_ohlc_values(df)
                points = self._serialize_ohlc(times, opens, highs, lows, closes)
                if len(points) >= min_points:
                    return points[-max(limit, min_points):]
            except Exception as exc:
                logger.warning("Falha histórico yfinance ticker para %s: %s", asset, exc)

        # Fallback HTTP direto Yahoo
        yahoo_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval={interval}"
        yahoo_json = self._http_get_json(yahoo_url, retries=3)
        if yahoo_json:
            try:
                result = (yahoo_json.get("chart") or {}).get("result") or []
                if result:
                    first = result[0]
                    timestamps = first.get("timestamp") or []
                    indicators = ((first.get("indicators") or {}).get("quote") or [{}])[0]
                    opens = indicators.get("open") or []
                    highs = indicators.get("high") or []
                    lows = indicators.get("low") or []
                    closes = indicators.get("close") or []
                    parsed_points: list[dict[str, Any]] = []
                    for ts, o, h, l, c in zip(timestamps, opens, highs, lows, closes):
                        dt = datetime.fromtimestamp(float(ts), tz=timezone.utc)
                        candle = self._sanitize_candle(
                            {
                                "time": dt.isoformat(),
                                "open": o,
                                "high": h,
                                "low": l,
                                "close": c,
                            }
                        )
                        if candle:
                            parsed_points.append(candle)
                    points = parsed_points
                    if len(points) >= min_points:
                        return points[-max(limit, min_points):]
            except Exception as exc:
                logger.warning("Falha parse Yahoo HTTP para %s: %s", asset, exc)

        # Fallback HTTP direto BRAPI (retry)
        brapi_interval = self._to_brapi_interval(timeframe)
        brapi_url = f"https://brapi.dev/api/quote/{asset}?range=5d&interval={brapi_interval}&fundamental=false"
        brapi_json = self._http_get_json(brapi_url, retries=3)
        if brapi_json:
            try:
                results = brapi_json.get("results") or []
                parsed_points: list[dict[str, Any]] = []
                if results:
                    prices = results[0].get("historicalDataPrice") or []
                    for row in prices:
                        close = row.get("close")
                        open_v = row.get("open")
                        high_v = row.get("high")
                        low_v = row.get("low")
                        ts = row.get("date")
                        if close is None or ts is None:
                            continue
                        dt = datetime.fromtimestamp(float(ts), tz=timezone.utc)
                        candle = self._sanitize_candle(
                            {
                                "time": dt.isoformat(),
                                "open": open_v,
                                "high": high_v,
                                "low": low_v,
                                "close": close,
                            }
                        )
                        if candle:
                            parsed_points.append(candle)
                points = parsed_points
                if len(points) >= min_points:
                    return points[-max(limit, min_points):]
            except Exception as exc:
                logger.warning("Falha parse BRAPI para %s: %s", asset, exc)

        points = self._ensure_min_points(points, min_points)
        return points[-max(limit, min_points):] if points else []

    def fetch_history(
        self,
        asset: str,
        timeframe: str = "5m",
        limit: int = 60,
        min_points: int = 30,
        cache_ttl_seconds: int = 300,
    ) -> list[dict[str, Any]]:
        asset = asset.upper()
        min_points = max(2, int(min_points))
        limit = max(int(limit), min_points)

        cache_key = f"{asset}:{self._to_ccxt_timeframe(timeframe)}:{limit}:{min_points}"
        now = time.time()
        cached = self._history_cache.get(cache_key)
        if cached and (now - cached[0]) <= cache_ttl_seconds:
            return cached[1]

        if self._is_crypto_asset(asset):
            points = self._fetch_crypto_history(asset, timeframe, limit, min_points)
        else:
            points = self._fetch_b3_history(asset, timeframe, limit, min_points)

        points = self._ensure_min_points(points, min_points)
        result = points[-max(limit, min_points):] if points else []
        self._history_cache[cache_key] = (now, result)
        return result

    def fetch_spot_price(self, asset: str, cache_ttl_seconds: int = 60, db: Session | None = None) -> float | None:
        asset = asset.upper()
        now = time.time()
        cache = self._spot_cache.get(asset)
        if cache and (now - cache[0]) <= cache_ttl_seconds and cache[1] > 0:
            return cache[1]

        if self._is_crypto_asset(asset):
            try:
                client = self._build_public_client()
                ticker = client.fetch_ticker(f"{asset}/USDT")
                price = float(ticker.get("last") or ticker.get("close") or 0)
                if math.isfinite(price) and price > 0:
                    self._spot_cache[asset] = (now, price)
                    return price
            except Exception as exc:
                logger.warning("Falha spot cripto ccxt para %s: %s", asset, exc)

        symbol = self._to_yfinance_ticker(asset)

        quote_url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbol}"
        quote_json = self._http_get_json(quote_url, retries=2)
        if quote_json:
            try:
                rows = ((quote_json.get("quoteResponse") or {}).get("result") or [])
                if rows:
                    price = float(rows[0].get("regularMarketPrice") or 0)
                    if math.isfinite(price) and price > 0:
                        self._spot_cache[asset] = (now, price)
                        return price
            except Exception:
                pass

        chart_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1m&range=1d"
        chart_json = self._http_get_json(chart_url, retries=2)
        if chart_json:
            try:
                result = (chart_json.get("chart") or {}).get("result") or []
                if result:
                    meta = result[0].get("meta") or {}
                    price = float(meta.get("regularMarketPrice") or meta.get("previousClose") or 0)
                    if math.isfinite(price) and price > 0:
                        self._spot_cache[asset] = (now, price)
                        return price
            except Exception:
                pass

        if not self._is_crypto_asset(asset):
            brapi_url = f"https://brapi.dev/api/quote/{asset}?fundamental=false"
            brapi_json = self._http_get_json(brapi_url, retries=2)
            if brapi_json:
                try:
                    rows = brapi_json.get("results") or []
                    if rows:
                        price = float(rows[0].get("regularMarketPrice") or rows[0].get("close") or 0)
                        if math.isfinite(price) and price > 0:
                            self._spot_cache[asset] = (now, price)
                            return price
                except Exception:
                    pass

        if yf is not None:
            try:
                ticker = yf.Ticker(symbol, session=YF_SESSION)
                fast_info = getattr(ticker, "fast_info", {}) or {}
                price = float(fast_info.get("lastPrice") or fast_info.get("regularMarketPrice") or 0)
                if math.isfinite(price) and price > 0:
                    self._spot_cache[asset] = (now, price)
                    return price
            except Exception:
                pass

        # Fallback estrito: buscar o último tick salvo no banco de dados para evitar retornar R$ 1,00
        if db is not None:
            last = (
                db.query(models.MarketTick)
                .filter(models.MarketTick.asset == asset)
                .order_by(models.MarketTick.tick_at.desc())
                .first()
            )
            if last and float(last.price) > 0:
                price = float(last.price)
                self._spot_cache[asset] = (now, price)
                return price

        return None
