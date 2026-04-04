from __future__ import annotations

import ccxt

from app import models


class ExchangeService:
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
