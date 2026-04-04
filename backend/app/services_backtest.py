from __future__ import annotations

import pandas as pd


def run_ma_backtest(
    prices: list[float],
    timestamps: list[pd.Timestamp],
    ma_short: int,
    ma_long: int,
    initial_capital: float = 10000.0,
) -> dict:
    df = pd.DataFrame({"close": prices}, index=pd.to_datetime(timestamps, utc=True))
    df = df.sort_index()

    df["ma_short"] = df["close"].rolling(ma_short).mean()
    df["ma_long"] = df["close"].rolling(ma_long).mean()
    df = df.dropna().copy()
    if df.empty:
        return {
            "equity_curve": [initial_capital],
            "total_return": 0.0,
            "win_rate": 0.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0,
        }

    df["signal"] = (df["ma_short"] > df["ma_long"]).astype(int)
    df["position"] = df["signal"].shift(1).fillna(0)
    df["returns"] = df["close"].pct_change().fillna(0)
    df["strategy_returns"] = df["returns"] * df["position"]

    df["equity"] = initial_capital * (1 + df["strategy_returns"]).cumprod()
    df["peak"] = df["equity"].cummax()
    df["drawdown"] = (df["equity"] - df["peak"]) / df["peak"]

    total_return = ((df["equity"].iloc[-1] / initial_capital) - 1) * 100
    max_drawdown = df["drawdown"].min() * 100

    trades = df[df["position"].diff().abs() > 0]
    trade_returns = trades["strategy_returns"]
    win_rate = float((trade_returns > 0).mean() * 100) if len(trade_returns) > 0 else 0.0

    std = df["strategy_returns"].std()
    sharpe = 0.0 if std == 0 or pd.isna(std) else float((df["strategy_returns"].mean() / std) * (252**0.5))

    return {
        "equity_curve": [float(v) for v in df["equity"].tolist()],
        "total_return": float(total_return),
        "win_rate": float(win_rate),
        "max_drawdown": float(max_drawdown),
        "sharpe_ratio": float(sharpe),
    }
