from fastapi import APIRouter, Query
from trading.backtesting.engine import BacktestConfig, BacktestEngine
from trading.backtesting.metrics import calculate_performance_metrics
from trading.data.synthetic import generate_synthetic_ohlcv
from trading.features.feature_pipeline import engineer_features
from trading.strategies.moving_average import MovingAverageCrossoverStrategy

router = APIRouter(prefix="/api", tags=["backtests"])


@router.get("/backtests/run")
async def run_backtest(
    symbol: str = "DEMO",
    limit: int = Query(default=60, ge=20, le=300),
    initial_cash: float = Query(default=100000.0, gt=0),
) -> dict[str, object]:
    market_data = generate_synthetic_ohlcv(symbol=symbol, periods=max(limit, 120), seed=7)
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
        "symbol": symbol.upper(),
        "initial_cash": float(result.initial_cash),
        "ending_cash": float(result.ending_cash),
        "ending_equity": float(result.ending_equity),
        "trade_count": int(len(result.trades)),
        "metrics": normalized_metrics,
    }
