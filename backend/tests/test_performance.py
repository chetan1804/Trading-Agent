import pandas as pd
from trading.backtesting.engine import BacktestConfig, BacktestEngine
from trading.backtesting.metrics import calculate_performance_metrics
from trading.performance.analytics import PerformanceAnalytics
from trading.strategies.moving_average import MovingAverageCrossoverStrategy


def test_performance_analytics_aggregates_equity_and_trade_metrics() -> None:
    bars = pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=6, freq="D"),
            "symbol": ["DEMO"] * 6,
            "open": [100, 100, 100, 120, 110, 105],
            "high": [101, 101, 111, 121, 111, 106],
            "low": [99, 99, 99, 109, 104, 104],
            "close": [100, 100, 110, 115, 105, 105],
            "volume": [1000] * 6,
            "sma_2": [0.5, 0.8, 2.0, 2.0, 1.0, 1.0],
            "sma_3": [1.0, 1.0, 1.0, 2.0, 2.0, 1.0],
        }
    )
    engine = BacktestEngine(
        BacktestConfig(
            initial_cash=1_000,
            position_size_fraction=1,
        )
    )
    result = engine.run(bars, MovingAverageCrossoverStrategy(2, 3))

    analytics = PerformanceAnalytics.from_backtest(result)
    report = analytics.snapshot()

    expected_total_return = calculate_performance_metrics(
        result.equity_curve,
        result.trades,
    )["total_return"]
    assert report["total_return"] == expected_total_return
    assert report["trade_count"] == 1
    assert report["max_drawdown"] < 0
    assert report["final_equity"] == result.ending_equity
