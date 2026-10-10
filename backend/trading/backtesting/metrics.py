import math

import numpy as np
import pandas as pd


def calculate_performance_metrics(
    equity_curve: pd.DataFrame,
    trades: pd.DataFrame,
    periods_per_year: float = 252.0,
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
    }
