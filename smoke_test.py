import asyncio
import json
import random
import string
import time
import urllib.error
import urllib.request

import websockets

BASE = "http://127.0.0.1:8000"


def req(method: str, path: str, data=None, token: str | None = None):
    body = None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if data is not None:
        body = json.dumps(data).encode("utf-8")

    request = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = {"raw": raw}
        return exc.code, parsed


def ensure(cond: bool, message: str):
    if not cond:
        raise RuntimeError(message)
    print(f"OK: {message}")


async def ws_check(asset: str):
    uri = f"ws://127.0.0.1:8000/ws/market/{asset}"
    async with websockets.connect(uri, open_timeout=10, close_timeout=5) as ws:
        await ws.send("ping")
        raw = await asyncio.wait_for(ws.recv(), timeout=12)
        payload = json.loads(raw)
        return payload.get("asset") == asset and float(payload.get("price", 0)) > 0


def main():
    status, data = req("GET", "/health")
    ensure(status == 200 and data.get("ok") is True, "health endpoint")

    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    email = f"smoke_{suffix}@botbot.local"
    password = "smoketest123"

    status, _ = req("POST", "/auth/register", {"email": email, "password": password})
    ensure(status == 200, "register user")

    status, auth = req("POST", "/auth/login", {"email": email, "password": password})
    ensure(status == 200 and "access_token" in auth, "login user")
    token = auth["access_token"]

    status, settings = req("GET", "/settings", token=token)
    ensure(status == 200 and "trade_mode" in settings, "fetch settings")

    strategy_payload = {"asset": "BTC", "timeframe": "5M", "ma_short_period": 9, "ma_long_period": 21}
    status, strategy = req("PUT", "/strategy/config", strategy_payload, token=token)
    ensure(status == 200 and strategy.get("asset") == "BTC", "update strategy")

    time.sleep(3)

    status, dashboard = req("GET", "/dashboard", token=token)
    ensure(status == 200 and dashboard.get("asset") == "BTC", "dashboard asset sync")
    ensure(isinstance(dashboard.get("chart"), list) and len(dashboard["chart"]) > 0, "dashboard chart available")

    ensure(asyncio.run(ws_check("BTC")), "websocket market stream BTC")

    status, paper = req("GET", "/paper/state?asset=BTC", token=token)
    ensure(status == 200 and paper.get("focus_asset") == "BTC", "paper state fetch")
    price = float(paper.get("current_price") or 0)
    ensure(price > 0, "paper current price available")

    status, buy = req("POST", "/paper/buy", {"asset": "BTC", "price": price, "quantity": 0.001}, token=token)
    ensure(status == 200 and buy.get("side") == "buy", "paper buy order")

    status, paper2 = req("GET", "/paper/state?asset=BTC", token=token)
    ensure(status == 200 and float(paper2.get("open_position_qty") or 0) > 0, "paper position opened")

    status, close = req("POST", "/paper/close", {}, token=token)
    ensure(status == 200 and close.get("side") == "sell", "paper close position")

    status, reset = req("POST", "/paper/reset", {}, token=token)
    ensure(status == 200 and abs(float(reset.get("balance") or 0) - 10000.0) < 0.01, "paper reset balance")
    ensure(float(reset.get("open_position_qty") or 0) == 0.0, "paper reset position")

    status, backtest = req("POST", "/backtest/run", {"period_label": "1 Month", "asset": "BTC"}, token=token)
    ensure(status == 200 and len(backtest.get("equity_curve", [])) > 0, "backtest run")

    status, logs = req("GET", "/logs?limit=20", token=token)
    ensure(status == 200 and isinstance(logs, list), "logs list")
    ensure(len(logs) > 0, "logs populated")

    print("\nSMOKE TEST RESULT: PASS")


if __name__ == "__main__":
    main()
