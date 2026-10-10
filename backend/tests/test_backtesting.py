from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest
from trading.backtesting.costs import TransactionCosts
from trading.backtesting.engine import BacktestConfig, BacktestEngine
from trading.backtesting.metrics import calculate_performance_metrics
from trading.strategies.moving_average import MovingAverageCrossoverStrategy


def _bars() -> pd.DataFrame:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    return pd.DataFrame(
        {
            "timestamp": [start + timedelta(days=index) for index in range(6)],
            "symbol": "DEMO",
            "open": [100, 100, 100, 120, 110, 105],
            "high": [101, 101, 111, 121, 111, 106],
            "low": [99, 99, 99, 109, 104, 104],
            "close": [100, 100, 110, 115, 105, 105],
            "volume": [1000] * 6,
            "sma_2": [0.5, 0.8, 2.0, 2.0, 1.0, 1.0],
            "sma_3": [1.0, 1.0, 1.0, 2.0, 2.0, 1.0],
        }
    )


def _engine(costs: TransactionCosts | None = None) -> BacktestEngine:
    return BacktestEngine(
        BacktestConfig(
            initial_cash=1_000,
            position_size_fraction=1,
            costs=costs
            if costs is not None
            else TransactionCosts(
                commission_rate=0,
                slippage_bps=0,
                spread_bps=0,
            ),
        )
    )


def test_backtest_fills_next_bar_open_and_closes_position() -> None:
    result = _engine().run(_bars(), MovingAverageCrossoverStrategy(2, 3))

    assert len(result.trades) == 1
    trade = result.trades.iloc[0]
    assert trade["entry_price"] == 120
    assert trade["exit_price"] == 105
    assert trade["holding_bars"] == 2
    assert result.open_position is None
    assert result.ending_cash == pytest.approx(875)
    assert result.ending_equity == pytest.approx(875)


def test_transaction_costs_use_adverse_fills_and_commissions() -> None:
    costs = TransactionCosts(commission_rate=0.001, slippage_bps=20, spread_bps=10)
    result = _engine(costs).run(_bars(), MovingAverageCrossoverStrategy(2, 3))
    trade = result.trades.iloc[0]

    assert trade["entry_price"] == pytest.approx(120.3)
    assert trade["exit_price"] == pytest.approx(104.7375)
    assert trade["entry_commission"] > 0
    assert trade["exit_commission"] > 0
    assert result.ending_cash < 875


def test_default_transaction_costs_are_not_frictionless() -> None:
    costs = TransactionCosts()

    assert costs.fill_price(100, "BUY") > 100
    assert costs.fill_price(100, "SELL") < 100
    assert costs.commission(100) > 0


def test_final_unclosed_position_is_marked_to_market() -> None:
    data = _bars().iloc[:4]
    result = _engine().run(data, MovingAverageCrossoverStrategy(2, 3))

    assert result.open_position is not None
    assert result.open_position.entry_time == data.iloc[3]["timestamp"].to_pydatetime()
    assert len(result.trades) == 0
    expected_equity = result.ending_cash + result.open_position.quantity * 115
    assert result.ending_equity == pytest.approx(expected_equity)


def test_backtest_requires_one_symbol_and_valid_configuration() -> None:
    data = pd.concat([_bars(), _bars().assign(symbol="OTHER")], ignore_index=True)
    with pytest.raises(ValueError, match="exactly one symbol"):
        _engine().run(data, MovingAverageCrossoverStrategy(2, 3))
    with pytest.raises(ValueError, match="initial_cash"):
        BacktestConfig(initial_cash=0)
    with pytest.raises(ValueError, match="cannot be negative"):
        TransactionCosts(slippage_bps=-1)


def test_metrics_calculate_returns_drawdown_and_trade_statistics() -> None:
    result = _engine().run(_bars(), MovingAverageCrossoverStrategy(2, 3))
    metrics = calculate_performance_metrics(result.equity_curve, result.trades)

    assert metrics["total_return"] == pytest.approx(-0.125)
    assert metrics["trade_count"] == 1
    assert metrics["win_rate"] == 0
    assert metrics["max_drawdown"] == pytest.approx(-0.125)
    assert metrics["exposure"] > 0
