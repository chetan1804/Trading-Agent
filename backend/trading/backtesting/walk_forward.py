from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from trading.backtesting.engine import BacktestConfig, BacktestEngine
from trading.backtesting.metrics import calculate_performance_metrics
from trading.data.validation import validate_ohlcv
from trading.strategies.base import Strategy


@dataclass(frozen=True)
class WalkForwardConfig:
    training_window: int = 252
    validation_window: int = 63
    test_window: int = 63
    step_size: int = 63

    def __post_init__(self) -> None:
        if min(self.training_window, self.validation_window, self.test_window, self.step_size) < 1:
            raise ValueError("walk-forward window sizes must be positive")


@dataclass(frozen=True)
class WalkForwardFold:
    fold: int
    training_start: datetime
    training_end: datetime
    validation_start: datetime
    validation_end: datetime
    test_start: datetime
    test_end: datetime
    metrics: dict[str, float | int]


@dataclass(frozen=True)
class WalkForwardResult:
    symbol: str
    folds: list[WalkForwardFold]


StrategyBuilder = Callable[[pd.DataFrame, pd.DataFrame], Strategy]


def run_walk_forward(
    market_data: pd.DataFrame,
    strategy_builder: StrategyBuilder,
    *,
    config: WalkForwardConfig | None = None,
    backtest_config: BacktestConfig | None = None,
) -> WalkForwardResult:
    """Fit with each fold's past data and report metrics only on its later test window."""
    settings = config or WalkForwardConfig()
    report = validate_ohlcv(market_data, max_abs_close_return=None)
    if report.has_errors:
        codes = sorted({issue.code for issue in report.issues if issue.severity == "error"})
        raise ValueError(f"Cannot run walk-forward validation on invalid data: {', '.join(codes)}")
    if report.data.empty:
        raise ValueError("market_data cannot be empty")

    frame = report.data.sort_values("timestamp", kind="stable").reset_index(drop=True)
    symbols = frame["symbol"].dropna().astype(str).unique()
    if len(symbols) != 1:
        raise ValueError("walk-forward validation currently supports exactly one symbol")

    minimum_rows = settings.training_window + settings.validation_window + settings.test_window
    if len(frame) < minimum_rows:
        raise ValueError(
            f"at least {minimum_rows} rows are required for the first walk-forward fold"
        )

    folds: list[WalkForwardFold] = []
    train_start = 0
    fold_number = 1
    while True:
        train_end = train_start + settings.training_window
        validation_end = train_end + settings.validation_window
        test_end = validation_end + settings.test_window
        if test_end > len(frame):
            break

        training = frame.iloc[train_start:train_end].copy()
        validation = frame.iloc[train_end:validation_end].copy()
        test = frame.iloc[validation_end:test_end].copy()
        strategy = strategy_builder(training, validation)
        result = BacktestEngine(backtest_config).run(test, strategy)
        metrics = calculate_performance_metrics(result.equity_curve, result.trades)
        folds.append(
            WalkForwardFold(
                fold=fold_number,
                training_start=pd.Timestamp(training["timestamp"].iloc[0]).to_pydatetime(),
                training_end=pd.Timestamp(training["timestamp"].iloc[-1]).to_pydatetime(),
                validation_start=pd.Timestamp(validation["timestamp"].iloc[0]).to_pydatetime(),
                validation_end=pd.Timestamp(validation["timestamp"].iloc[-1]).to_pydatetime(),
                test_start=pd.Timestamp(test["timestamp"].iloc[0]).to_pydatetime(),
                test_end=pd.Timestamp(test["timestamp"].iloc[-1]).to_pydatetime(),
                metrics=metrics,
            )
        )
        fold_number += 1
        train_start += settings.step_size

    return WalkForwardResult(symbol=str(symbols[0]), folds=folds)
