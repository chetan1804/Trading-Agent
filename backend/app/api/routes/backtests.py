import math

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, Request
from trading.backtesting.engine import BacktestConfig, BacktestEngine
from trading.backtesting.metrics import (
    calculate_monthly_returns,
    calculate_performance_metrics,
    calculate_trade_distribution,
)
from trading.backtesting.walk_forward import WalkForwardConfig, run_walk_forward
from trading.data.synthetic import generate_synthetic_ohlcv
from trading.features.feature_pipeline import engineer_features
from trading.strategies.buy_hold import BuyAndHoldStrategy
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
    limit: int = Query(default=60, ge=20, le=300),
    initial_cash: float = Query(default=100000.0, gt=0),
) -> dict[str, object]:
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
    run_data = feature_frame.tail(limit).reset_index(drop=True)
    strategy = MovingAverageCrossoverStrategy(fast_window=20, slow_window=50)
    engine = BacktestEngine(BacktestConfig(initial_cash=initial_cash))
    result = engine.run(run_data, strategy)
    metrics = calculate_performance_metrics(
        result.equity_curve, result.trades, turnover_value=result.turnover
    )
    benchmark = engine.run(run_data, BuyAndHoldStrategy())
    benchmark_metrics = calculate_performance_metrics(
        benchmark.equity_curve,
        benchmark.trades,
        turnover_value=benchmark.turnover,
    )

    normalized_metrics = _finite_metrics(metrics)
    return {
        "symbol": symbol_upper,
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
            "moving_average": normalized_metrics,
            "buy_and_hold": _finite_metrics(benchmark_metrics),
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
    try:
        result = run_walk_forward(
            featured_data,
            lambda _training, _validation: MovingAverageCrossoverStrategy(),
            config=config,
            backtest_config=BacktestConfig(initial_cash=initial_cash),
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    return {
        "symbol": result.symbol,
        "data_source": data_source,
        "fold_count": len(result.folds),
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
            }
            for fold in result.folds
        ],
    }
