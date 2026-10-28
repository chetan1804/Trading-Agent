import math

import numpy as np
import pandas as pd


def calculate_performance_metrics(
    equity_curve: pd.DataFrame,
    trades: pd.DataFrame,
    periods_per_year: float = 252.0,
    turnover_value: float = 0.0,
) -> dict[str, float | int]:
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive")
    if equity_curve.empty:
        raise ValueError("equity_curve cannot be empty")
    equity = pd.to_numeric(equity_curve["equity"], errors="raise")
    returns = equity.pct_change(fill_method=None).dropna()
    initial_equity = float(equity.iloc[0])
    final_equity = float(equity.iloc[-1])
    total_return = final_equity / initial_equity - 1

    duration_days = (
        pd.Timestamp(equity_curve["timestamp"].iloc[-1])
        - pd.Timestamp(equity_curve["timestamp"].iloc[0])
    ).total_seconds() / 86_400
    cagr = (
        (final_equity / initial_equity) ** (365.25 / duration_days) - 1
        if duration_days > 0 and final_equity > 0
        else 0.0
    )
    volatility = float(returns.std(ddof=1)) if len(returns) > 1 else 0.0
    sharpe = float(returns.mean() / volatility * math.sqrt(periods_per_year)) if volatility else 0.0
    downside = returns.clip(upper=0)
    downside_deviation = float(np.sqrt(np.mean(np.square(downside)))) if len(downside) else 0.0
    sortino = (
        float(returns.mean() / downside_deviation * math.sqrt(periods_per_year))
        if downside_deviation
        else 0.0
    )
    drawdown = equity / equity.cummax() - 1
    max_drawdown = float(drawdown.min())
    calmar = cagr / abs(max_drawdown) if max_drawdown < 0 else 0.0

    trade_pnl = pd.to_numeric(trades.get("pnl", pd.Series(dtype=float)), errors="raise")
    winners = trade_pnl[trade_pnl > 0]
    losers = trade_pnl[trade_pnl < 0]
    gross_profit = float(winners.sum())
    gross_loss = float(-losers.sum())
    profit_factor = gross_profit / gross_loss if gross_loss else (math.inf if gross_profit else 0.0)
    exposure = (pd.to_numeric(equity_curve["exposure"], errors="raise") / equity).mean()
    holding_periods = pd.to_numeric(trades.get("holding_bars", pd.Series(dtype=float)))
    average_equity = float(equity.mean())

    return {
        "total_return": total_return,
        "cagr": cagr,
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "max_drawdown": max_drawdown,
        "calmar_ratio": calmar,
        "win_rate": float((trade_pnl > 0).mean()) if len(trade_pnl) else 0.0,
        "loss_rate": float((trade_pnl < 0).mean()) if len(trade_pnl) else 0.0,
        "profit_factor": profit_factor,
        "average_win": float(winners.mean()) if len(winners) else 0.0,
        "average_loss": float(losers.mean()) if len(losers) else 0.0,
        "expectancy": float(trade_pnl.mean()) if len(trade_pnl) else 0.0,
        "trade_count": int(len(trade_pnl)),
        "average_holding_bars": float(holding_periods.mean()) if len(holding_periods) else 0.0,
        "exposure": float(exposure),
        "turnover": float(turnover_value),
        "turnover_ratio": float(turnover_value / average_equity) if average_equity else 0.0,
    }


def calculate_monthly_returns(equity_curve: pd.DataFrame) -> dict[str, float]:
    if equity_curve.empty:
        return {}
    values = pd.to_numeric(equity_curve["equity"], errors="raise")
    timestamps = pd.to_datetime(equity_curve["timestamp"], utc=True, errors="raise")
    series = pd.Series(values.to_numpy(), index=timestamps).sort_index()
    first_timestamp = series.index[0]
    month_start = first_timestamp.replace(
        day=1, hour=0, minute=0, second=0, microsecond=0, nanosecond=0
    )
    baseline_time = month_start - pd.Timedelta(nanoseconds=1)
    # The engine's first equity value is the starting capital before any return interval.
    series.loc[baseline_time] = float(values.iloc[0])
    month_ends = series.resample("ME").last().dropna()
    returns = month_ends.pct_change(fill_method=None).dropna()
    return {timestamp.strftime("%Y-%m"): float(value) for timestamp, value in returns.items()}


def calculate_trade_distribution(trades: pd.DataFrame) -> dict[str, object]:
    pnl = pd.to_numeric(trades.get("pnl", pd.Series(dtype=float)), errors="raise")
    holding = pd.to_numeric(trades.get("holding_bars", pd.Series(dtype=float)), errors="raise")
    return {
        "outcomes": {
            "wins": int((pnl > 0).sum()),
            "losses": int((pnl < 0).sum()),
            "breakeven": int((pnl == 0).sum()),
        },
        "holding_bars": {
            "1": int((holding <= 1).sum()),
            "2_to_5": int(holding.between(2, 5).sum()),
            "6_to_20": int(holding.between(6, 20).sum()),
            "over_20": int((holding > 20).sum()),
        },
    }
