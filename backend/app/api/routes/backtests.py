import math
import statistics
from datetime import date, timedelta
from typing import Literal

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, Request
from trading.backtesting.costs import TransactionCosts
from trading.backtesting.engine import BacktestConfig, BacktestEngine
from trading.backtesting.metrics import (
    calculate_monthly_returns,
    calculate_performance_metrics,
    calculate_trade_distribution,
)
from trading.backtesting.walk_forward import WalkForwardConfig, run_walk_forward
from trading.data.synthetic import generate_synthetic_ohlcv
from trading.features.feature_pipeline import engineer_features
from trading.ml.targets import next_period_direction
from trading.ml.trainer import SignalModelTrainer
from trading.strategies.buy_hold import BuyAndHoldStrategy
from trading.strategies.ml_strategy import MLProbabilityStrategy
from trading.strategies.moving_average import MovingAverageCrossoverStrategy

router = APIRouter(prefix="/api", tags=["backtests"])


def _finite_metrics(metrics: dict[str, float | int]) -> dict[str, float | int | None]:
    return {
        key: float(value) if isinstance(value, (int, float)) and math.isfinite(value) else None
        for key, value in metrics.items()
    }


@router.get("/backtests/run")
async def run_backtest(
    request: Request,
    symbol: str = "RELIANCE.NS",
    strategy_id: Literal["moving_average", "buy_and_hold"] = "moving_average",
    limit: int = Query(default=60, ge=20, le=300),
    initial_cash: float = Query(default=100000.0, gt=0),
    commission_rate: float = Query(default=0.001, ge=0, lt=1),
    slippage_bps: float = Query(default=5.0, ge=0),
    spread_bps: float = Query(default=2.0, ge=0),
    stop_loss_fraction: float | None = Query(default=None, gt=0, le=1),
    take_profit_fraction: float | None = Query(default=None, gt=0, le=1),
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, object]:
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=422, detail="start_date must be on or before end_date")
    symbol_upper = symbol.upper()
    store = getattr(request.app.state, "market_data_store", {})
    stored_bars = store.get(symbol_upper, [])
    if stored_bars:
        # Engineer indicators over the complete history so the requested window
        # retains its warm-up values and can detect crossovers at its boundary.
        market_data = pd.DataFrame(stored_bars)
        market_data["symbol"] = symbol_upper
        data_source = "ingested"
    else:
        market_data = generate_synthetic_ohlcv(
            symbol=symbol_upper,
            periods=max(limit, 120),
            seed=7,
        )
        data_source = "synthetic"

    feature_frame = engineer_features(market_data)
    timestamps = pd.to_datetime(feature_frame["timestamp"], utc=True)
    if start_date:
        feature_frame = feature_frame.loc[
            timestamps >= pd.Timestamp(start_date, tz="UTC")
        ]
        timestamps = pd.to_datetime(feature_frame["timestamp"], utc=True)
    if end_date:
        end_exclusive = pd.Timestamp(end_date + timedelta(days=1), tz="UTC")
        feature_frame = feature_frame.loc[timestamps < end_exclusive]
    run_data = feature_frame.tail(limit).reset_index(drop=True)
    if run_data.empty:
        raise HTTPException(status_code=422, detail="no market bars fall within the selected range")

    costs = TransactionCosts(
        commission_rate=commission_rate,
        slippage_bps=slippage_bps,
        spread_bps=spread_bps,
    )
    engine = BacktestEngine(
        BacktestConfig(
            initial_cash=initial_cash,
            costs=costs,
            stop_loss_fraction=stop_loss_fraction,
            take_profit_fraction=take_profit_fraction,
        )
    )
    moving_average_result = engine.run(
        run_data,
        MovingAverageCrossoverStrategy(fast_window=20, slow_window=50),
    )
    buy_and_hold_result = engine.run(run_data, BuyAndHoldStrategy())
    result = moving_average_result if strategy_id == "moving_average" else buy_and_hold_result
    metrics = calculate_performance_metrics(
        result.equity_curve, result.trades, turnover_value=result.turnover
    )
    moving_average_metrics = calculate_performance_metrics(
        moving_average_result.equity_curve,
        moving_average_result.trades,
        turnover_value=moving_average_result.turnover,
    )
    buy_and_hold_metrics = calculate_performance_metrics(
        buy_and_hold_result.equity_curve,
        buy_and_hold_result.trades,
        turnover_value=buy_and_hold_result.turnover,
    )

    normalized_metrics = _finite_metrics(metrics)
    return {
        "symbol": symbol_upper,
        "strategy_id": strategy_id,
        "data_source": data_source,
        "initial_cash": float(result.initial_cash),
        "ending_cash": float(result.ending_cash),
        "ending_equity": float(result.ending_equity),
        "trade_count": int(len(result.trades)),
        "metrics": normalized_metrics,
        "monthly_returns": calculate_monthly_returns(result.equity_curve),
        "trade_distribution": calculate_trade_distribution(result.trades),
        "trades": [
            {
                "symbol": str(row.symbol),
                "strategy_id": str(row.strategy_id),
                "entry_time": pd.Timestamp(row.entry_time).isoformat(),
                "exit_time": pd.Timestamp(row.exit_time).isoformat(),
                "quantity": float(row.quantity),
                "entry_price": float(row.entry_price),
                "exit_price": float(row.exit_price),
                "pnl": float(row.pnl),
                "return_fraction": float(row.return_fraction),
                "holding_bars": int(row.holding_bars),
                "exit_reason": str(row.exit_reason),
            }
            for row in result.trades.itertuples(index=False)
        ],
        "equity_curve": [
            {
                "timestamp": pd.Timestamp(row.timestamp).isoformat(),
                "equity": float(row.equity),
                "drawdown": float(row.drawdown),
            }
            for row in result.equity_curve.itertuples(index=False)
        ],
        "comparison": {
            "moving_average": _finite_metrics(moving_average_metrics),
            "buy_and_hold": _finite_metrics(buy_and_hold_metrics),
        },
    }


@router.get("/backtests/walk-forward")
async def walk_forward_backtest(
    request: Request,
    symbol: str = "RELIANCE.NS",
    limit: int = Query(default=1000, ge=3, le=10000),
    training_window: int = Query(default=252, ge=1),
    validation_window: int = Query(default=63, ge=1),
    test_window: int = Query(default=63, ge=1),
    step_size: int = Query(default=63, ge=1),
    initial_cash: float = Query(default=100000.0, gt=0),
    strategy_id: Literal["moving_average", "ml_probability"] = "moving_average",
    model_type: Literal["logistic_regression", "random_forest"] = "logistic_regression",
    buy_threshold: float = Query(default=0.65, gt=0, le=1),
    sell_threshold: float = Query(default=0.35, ge=0, lt=1),
    stop_loss_fraction: float | None = Query(default=None, gt=0, le=1),
    take_profit_fraction: float | None = Query(default=None, gt=0, le=1),
) -> dict[str, object]:
    symbol_upper = symbol.upper()
    store = getattr(request.app.state, "market_data_store", {})
    stored_bars = store.get(symbol_upper, [])
    if stored_bars:
        market_data = pd.DataFrame(stored_bars)
        market_data["symbol"] = symbol_upper
        data_source = "ingested"
    else:
        market_data = generate_synthetic_ohlcv(
            symbol=symbol_upper,
            periods=limit,
            seed=7,
        )
        data_source = "synthetic"

    featured_data = engineer_features(market_data).tail(limit).reset_index(drop=True)
    config = WalkForwardConfig(
        training_window=training_window,
        validation_window=validation_window,
        test_window=test_window,
        step_size=step_size,
    )
    if strategy_id == "ml_probability" and sell_threshold >= buy_threshold:
        raise HTTPException(
            status_code=422,
            detail="sell_threshold must be less than buy_threshold",
        )

    def build_strategy(training: pd.DataFrame, validation: pd.DataFrame):
        if strategy_id == "moving_average":
            return MovingAverageCrossoverStrategy()

        # The final training label uses the first validation close. At the end
        # of validation, that outcome is known; no test rows enter model fitting.
        available = pd.concat([training, validation], ignore_index=True)
        training_frame = training.reset_index(drop=True)
        labels = (
            next_period_direction(available["close"])
            .iloc[: len(training)]
            .reset_index(drop=True)
        )
        feature_names = [
            column
            for column in training_frame.select_dtypes(include="number").columns
            if column not in {"open", "high", "low", "close", "volume"}
        ]
        usable = labels.notna()
        for column in feature_names:
            usable &= training_frame[column].notna() & training_frame[column].map(math.isfinite)
        fit_rows = training_frame.loc[usable]
        fit_labels = labels.loc[usable].astype(int)
        artifact = SignalModelTrainer().fit_artifact(
            features={
                column: fit_rows[column].astype(float).tolist() for column in feature_names
            },
            labels=fit_labels.tolist(),
            model_type=model_type,
        )
        return MLProbabilityStrategy(
            artifact=artifact,
            feature_names=tuple(feature_names),
            buy_threshold=buy_threshold,
            sell_threshold=sell_threshold,
            model_version=f"walk-forward-{model_type}",
        )

    try:
        result = run_walk_forward(
            featured_data,
            build_strategy,
            config=config,
            backtest_config=BacktestConfig(
                initial_cash=initial_cash,
                stop_loss_fraction=stop_loss_fraction,
                take_profit_fraction=take_profit_fraction,
            ),
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    def summarize(metrics: list[dict[str, float | int | None]]) -> dict[str, float | int]:
        returns = [float(item.get("total_return") or 0.0) for item in metrics]
        drawdowns = [float(item.get("max_drawdown") or 0.0) for item in metrics]
        sharpes = [float(item.get("sharpe_ratio") or 0.0) for item in metrics]
        profitable_folds = sum(value > 0 for value in returns)
        return {
            "folds": len(metrics),
            "mean_return": statistics.mean(returns) if returns else 0.0,
            "median_return": statistics.median(returns) if returns else 0.0,
            "profitable_folds": profitable_folds,
            "profitable_fold_rate": profitable_folds / len(returns) if returns else 0.0,
            "worst_drawdown": min(drawdowns) if drawdowns else 0.0,
            "mean_sharpe_ratio": statistics.mean(sharpes) if sharpes else 0.0,
        }

    summary_metrics: dict[str, list[dict[str, float | int | None]]] = {
        strategy_id: [_finite_metrics(fold.metrics) for fold in result.folds]
    }
    for benchmark in ("moving_average", "buy_and_hold"):
        if benchmark != strategy_id:
            summary_metrics[benchmark] = [
                _finite_metrics(fold.comparison[benchmark])
                for fold in result.folds
                if benchmark in fold.comparison
            ]

    return {
        "symbol": result.symbol,
        "data_source": data_source,
        "strategy_id": strategy_id,
        "model_type": model_type if strategy_id == "ml_probability" else None,
        "fold_count": len(result.folds),
        "summary": {name: summarize(metrics) for name, metrics in summary_metrics.items()},
        "folds": [
            {
                "fold": fold.fold,
                "training_start": fold.training_start.isoformat(),
                "training_end": fold.training_end.isoformat(),
                "validation_start": fold.validation_start.isoformat(),
                "validation_end": fold.validation_end.isoformat(),
                "test_start": fold.test_start.isoformat(),
                "test_end": fold.test_end.isoformat(),
                "metrics": _finite_metrics(fold.metrics),
                "comparison": {
                    strategy: _finite_metrics(strategy_metrics)
                    for strategy, strategy_metrics in fold.comparison.items()
                    if strategy != strategy_id
                },
            }
            for fold in result.folds
        ],
    }
