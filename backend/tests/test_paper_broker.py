from datetime import UTC, datetime

import pytest
from trading.broker.order import Order, OrderStatus
from trading.broker.paper_broker import PaperBroker
from trading.risk.manager import RiskDecision, RiskManager

NOW = datetime(2024, 1, 2, tzinfo=UTC)


def test_order_tracks_fill_lifecycle() -> None:
    order = Order(symbol="AAPL", side="BUY", quantity=10, limit_price=100.0)

    assert order.status is OrderStatus.NEW
    assert order.remaining_quantity == pytest.approx(10)

    order.apply_fill(4, 99.0)
    assert order.status is OrderStatus.PARTIALLY_FILLED
    assert order.filled_quantity == pytest.approx(4)
    assert order.remaining_quantity == pytest.approx(6)

    order.apply_fill(6, 101.0)
    assert order.status is OrderStatus.FILLED
    assert order.filled_quantity == pytest.approx(10)
    assert order.avg_fill_price == pytest.approx(100.2)
    assert order.remaining_quantity == pytest.approx(0)


def test_paper_broker_rejects_risk_denied_orders() -> None:
    broker = PaperBroker(initial_cash=100_000.0, risk_manager=RiskManager(enabled=True))

    order = Order(symbol="MSFT", side="BUY", quantity=5, limit_price=200.0)
    broker.submit_order(order, risk_decision=RiskDecision(False, "maximum drawdown reached"))

    stored = broker.get_order(order.id)
    assert stored is not None
    assert stored.status is OrderStatus.REJECTED
    assert stored.rejection_reason == "maximum drawdown reached"


def test_paper_broker_executes_fills_and_updates_positions() -> None:
    broker = PaperBroker(initial_cash=50_000.0, slippage_bps=0.0)
    order = broker.create_order(symbol="NVDA", side="BUY", quantity=10, limit_price=100.0)

    broker.submit_order(order, market_price=101.0)
    assert order.status is OrderStatus.OPEN

    broker.fill_order(order.id, price=101.5, quantity=10)
    assert order.status is OrderStatus.FILLED
    assert broker.positions["NVDA"] == pytest.approx(10)
    assert broker.cash < 50_000.0
    assert broker.last_prices["NVDA"] == pytest.approx(101.5)


def test_cancelled_order_cannot_be_filled() -> None:
    broker = PaperBroker(initial_cash=10_000.0)
    order = broker.create_order(symbol="META", side="SELL", quantity=2, limit_price=250.0)

    broker.cancel_order(order.id)
    with pytest.raises(ValueError, match="cancelled"):
        broker.fill_order(order.id, price=250.0, quantity=2)
