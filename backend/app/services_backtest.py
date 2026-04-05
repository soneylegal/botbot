from __future__ import annotations

import pandas as pd


def run_ma_backtest(
    prices: list[float],
    timestamps: list[pd.Timestamp],
    ma_short: int,
    ma_long: int,
    initial_capital: float = 10000.0,
) -> dict:
    df = pd.DataFrame({"close": prices}, index=pd.to_datetime(timestamps, utc=True)).sort_index()
    df["ma_short"] = df["close"].rolling(ma_short).mean()
    df["ma_long"] = df["close"].rolling(ma_long).mean()
    df = df.dropna().copy()

    if df.empty:
        raise ValueError("Dados insuficientes para este período")

    cash = float(initial_capital)
    qty = 0.0
    entry_price = 0.0
    prev_signal = 0
    wins = 0
    trades = 0
    equity_curve: list[float] = []
    equity_timestamps: list[str] = []

    for ts, row in df.iterrows():
        price = float(row["close"])
        signal = 1 if float(row["ma_short"]) > float(row["ma_long"]) else 0

        if prev_signal == 0 and signal == 1 and qty == 0.0 and cash >= price:
            qty = cash / price
            cash -= qty * price
            entry_price = price

        elif prev_signal == 1 and signal == 0 and qty > 0.0:
            cash += qty * price
            trades += 1
            if entry_price > 0 and (price / entry_price - 1) > 0:
                wins += 1
            qty = 0.0
            entry_price = 0.0

        equity_curve.append(cash + qty * price)
        equity_timestamps.append(ts.isoformat())
        prev_signal = signal

    if qty > 0.0:
        last_price = float(df["close"].iloc[-1])
        cash += qty * last_price
        trades += 1
        if entry_price > 0 and (last_price / entry_price - 1) > 0:
            wins += 1
        qty = 0.0
        equity_curve[-1] = cash

    equity = pd.Series(equity_curve)
    returns = equity.pct_change().fillna(0.0)
    peak = equity.cummax()
    drawdown = (equity / peak) - 1.0

    total_return = ((equity.iloc[-1] / initial_capital) - 1.0) * 100.0
    max_drawdown = float(drawdown.min() * 100.0)
    win_rate = float((wins / trades) * 100.0) if trades else 0.0
    std = returns.std()
    sharpe = 0.0 if std == 0 or pd.isna(std) else float((returns.mean() / std) * (252 ** 0.5))

    return {
        "equity_curve": [float(v) for v in equity_curve],
        "equity_timestamps": equity_timestamps,
        "total_return": float(total_return),
        "win_rate": float(win_rate),
        "max_drawdown": float(max_drawdown),
        "sharpe_ratio": float(sharpe),
    }
