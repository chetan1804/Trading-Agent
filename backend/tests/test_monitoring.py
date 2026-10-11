from datetime import UTC, datetime, timedelta

import pytest
from trading.broker.paper_broker import PaperBroker
from trading.monitoring.execution import ExecutionMonitor


def test_execution_monitor_tracks_fill_quality_and_order_health() -> None:
    broker = PaperBroker(initial_cash=100_000.0, slippage_bps=0.0)
    buy_order = broker.create_order(symbol="AAPL", side="BUY", quantity=5, limit_price=100.0)
    broker.submit_order(buy_order, market_price=100.0)
    broker.fill_order(buy_order.id, price=100.5, quantity=5)

    sell_order = broker.create_order(symbol="AAPL", side="SELL", quantity=2, limit_price=105.0)
    broker.submit_order(sell_order, market_price=105.0)
    broker.fill_order(sell_order.id, price=104.5, quantity=2)

    monitor = ExecutionMonitor(broker)
    summary = monitor.snapshot()

    assert summary["open_orders"] == 0
    assert summary["filled_orders"] == 2
    assert summary["fills_by_symbol"]["AAPL"] == 2
    assert summary["avg_fill_slippage_bps"]["AAPL"] == pytest.approx(1.19047619047619)
    assert summary["order_health"]["AAPL"]["status"] == "healthy"


def test_execution_monitor_flags_stale_orders() -> None:
    broker = PaperBroker(initial_cash=10_000.0)
    order = broker.create_order(symbol="MSFT", side="BUY", quantity=3, limit_price=200.0)
    order.created_at = datetime(2024, 1, 1, tzinfo=UTC) - timedelta(hours=2)
    broker.orders[order.id] = order

    monitor = ExecutionMonitor(broker)
    report = monitor.snapshot()

    assert report["order_health"]["MSFT"]["status"] == "stale"
    assert report["stale_orders"] == 1
