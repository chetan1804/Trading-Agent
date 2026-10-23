import pandas as pd
from fastapi import APIRouter, Query, Request
from trading.backtesting.engine import BacktestConfig, BacktestEngine
from trading.backtesting.metrics import calculate_performance_metrics
from trading.data.synthetic import generate_synthetic_ohlcv
from trading.features.feature_pipeline import engineer_features
from trading.strategies.moving_average import MovingAverageCrossoverStrategy

router = APIRouter(prefix="/api", tags=["backtests"])


@router.get("/backtests/run")
async def run_backtest(
    request: Request,
    symbol: str = "DEMO",
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
    metrics = calculate_performance_metrics(result.equity_curve, result.trades)

    normalized_metrics = {
        key: float(value) if isinstance(value, (int, float)) else value
        for key, value in metrics.items()
    }
    return {
        "symbol": symbol_upper,
        "data_source": data_source,
        "initial_cash": float(result.initial_cash),
        "ending_cash": float(result.ending_cash),
        "ending_equity": float(result.ending_equity),
        "trade_count": int(len(result.trades)),
        "metrics": normalized_metrics,
    }
