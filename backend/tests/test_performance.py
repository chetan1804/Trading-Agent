import pandas as pd
from trading.backtesting.engine import BacktestConfig, BacktestEngine
from trading.backtesting.metrics import calculate_performance_metrics
from trading.broker.paper_broker import PaperBroker
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


def test_paper_account_risk_metrics_use_recorded_daily_equity_history() -> None:
    broker = PaperBroker(initial_cash=1_000)
    history = [
        {"captured_at": "2024-01-01T12:00:00Z", "equity": 1_000, "exposure": 0},
        {"captured_at": "2024-01-02T12:00:00Z", "equity": 1_100, "exposure": 500},
        {"captured_at": "2024-01-03T12:00:00Z", "equity": 900, "exposure": 400},
    ]

    report = PerformanceAnalytics.from_paper_broker(broker, history).snapshot()

    assert report["history_observations"] == 3
    assert abs(report["max_drawdown"] - (900 / 1_100 - 1)) < 1e-9
    assert "sharpe_ratio" in report


def test_paper_account_reports_realized_exit_fill_quality() -> None:
    broker = PaperBroker(initial_cash=10_000, fee_rate=0, slippage_bps=0)
    entry = broker.create_order(symbol="DEMO", side="BUY", quantity=4)
    broker.submit_order(entry, market_price=100)
    broker.fill_order(entry.id, price=100)
    winning_exit = broker.create_order(symbol="DEMO", side="SELL", quantity=2)
    broker.submit_order(winning_exit, market_price=110)
    broker.fill_order(winning_exit.id, price=110)
    losing_exit = broker.create_order(symbol="DEMO", side="SELL", quantity=1)
    broker.submit_order(losing_exit, market_price=90)
    broker.fill_order(losing_exit.id, price=90)

    report = PerformanceAnalytics.from_paper_broker(broker).snapshot()

    assert [item.realized_pnl for item in broker.executions] == [None, 20, -10]
    assert report["realized_exit_fill_count"] == 2
    assert report["winning_exit_fills"] == 1
    assert report["losing_exit_fills"] == 1
    assert report["win_rate"] == 0.5
    assert report["profit_factor"] == 2
    assert report["expectancy"] == 5
