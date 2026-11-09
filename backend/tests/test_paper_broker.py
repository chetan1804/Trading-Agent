from datetime import UTC, datetime, timedelta

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


def test_market_bar_triggers_gap_through_stop_and_marks_close() -> None:
    broker = PaperBroker(initial_cash=10_000, fee_rate=0, slippage_bps=0)
    entry = broker.create_order(symbol="DEMO", side="BUY", quantity=10)
    broker.submit_order(entry, market_price=100)
    broker.fill_order(entry.id, price=100, timestamp=NOW - timedelta(minutes=1))
    stop = broker.create_order(
        symbol="DEMO", side="SELL", quantity=10, order_type="STOP", stop_price=95
    )
    broker.submit_order(stop, market_price=100)

    match = broker.process_market_bar(
        symbol="demo", open_price=90, high=93, low=89, close=92, timestamp=NOW
    )

    assert match.triggered_orders == [stop]
    assert match.cancelled_orders == []
    assert stop.status is OrderStatus.FILLED
    assert stop.avg_fill_price == pytest.approx(90)
    assert broker.positions == {}
    assert broker.last_prices["DEMO"] == pytest.approx(92)
    assert broker.daily_pnl == pytest.approx(-100)


def test_limit_fill_respects_limit_price_after_slippage() -> None:
    broker = PaperBroker(initial_cash=10_000, fee_rate=0, slippage_bps=100)
    order = broker.create_order(
        symbol="DEMO", side="BUY", quantity=10, order_type="LIMIT", limit_price=95
    )
    broker.submit_order(order, market_price=95)

    match = broker.process_market_bar(
        symbol="DEMO", open_price=90, high=96, low=89, close=93
    )

    assert match.triggered_orders == [order]
    assert order.status is OrderStatus.FILLED
    assert order.avg_fill_price == pytest.approx(90.9)


def test_oco_stop_fill_cancels_take_profit_even_when_both_levels_hit() -> None:
    broker = PaperBroker(initial_cash=10_000, fee_rate=0, slippage_bps=0)
    entry = broker.create_order(symbol="DEMO", side="BUY", quantity=10)
    broker.submit_order(entry, market_price=100)
    broker.fill_order(entry.id, price=100)
    target = broker.create_order(
        symbol="DEMO",
        side="SELL",
        quantity=10,
        order_type="LIMIT",
        limit_price=110,
        oco_group="position-1",
    )
    stop = broker.create_order(
        symbol="DEMO",
        side="SELL",
        quantity=10,
        order_type="STOP",
        stop_price=95,
        oco_group="position-1",
    )
    broker.submit_order(target, market_price=100)
    broker.submit_order(stop, market_price=100)

    match = broker.process_market_bar(
        symbol="DEMO", open_price=100, high=115, low=90, close=105
    )

    assert match.triggered_orders == [stop]
    assert match.cancelled_orders == [target]
    assert stop.status is OrderStatus.FILLED
    assert target.status is OrderStatus.CANCELLED
    assert broker.positions == {}


def test_stop_and_limit_order_types_require_trigger_prices() -> None:
    with pytest.raises(ValueError, match="limit orders require"):
        Order(symbol="DEMO", side="BUY", quantity=1, order_type="LIMIT")
    with pytest.raises(ValueError, match="stop orders require"):
        Order(symbol="DEMO", side="SELL", quantity=1, order_type="STOP")


def test_oco_orders_must_match_symbol_side_and_quantity() -> None:
    broker = PaperBroker(initial_cash=10_000)
    stop = broker.create_order(
        symbol="DEMO",
        side="SELL",
        quantity=10,
        order_type="STOP",
        stop_price=95,
        oco_group="position-1",
    )
    broker.submit_order(stop, market_price=100)
    mismatched = broker.create_order(
        symbol="OTHER",
        side="SELL",
        quantity=10,
        order_type="LIMIT",
        limit_price=110,
        oco_group="position-1",
    )

    broker.submit_order(mismatched, market_price=110)

    assert mismatched.status is OrderStatus.REJECTED
    assert mismatched.rejection_reason == "OCO orders must match symbol, side, and quantity"


def test_market_updates_reject_duplicate_or_out_of_order_bars_and_restore_cursor() -> None:
    broker = PaperBroker(initial_cash=10_000)
    first = {
        "symbol": "DEMO",
        "open_price": 100,
        "high": 102,
        "low": 99,
        "close": 101,
        "timestamp": NOW,
    }
    broker.process_market_bar(**first)

    with pytest.raises(ValueError, match="later than the previous update"):
        broker.process_market_bar(**first)
    with pytest.raises(ValueError, match="later than the previous update"):
        broker.process_market_bar(**{**first, "timestamp": NOW - timedelta(minutes=1)})

    restored = PaperBroker(initial_cash=1)
    restored.restore_state(broker.snapshot_state())
    assert restored.last_market_timestamp_by_symbol == {"DEMO": NOW}


def test_partial_fills_create_auditable_executions_and_retry_idempotently() -> None:
    broker = PaperBroker(initial_cash=10_000, fee_rate=0, slippage_bps=0)
    order = broker.create_order(symbol="DEMO", side="BUY", quantity=10)
    broker.submit_order(order, market_price=100)

    broker.fill_order(
        order.id,
        price=100,
        quantity=4,
        timestamp=NOW,
        idempotency_key="fill-request-1",
    )
    retry = broker.fill_order(
        order.id,
        price=100,
        quantity=4,
        timestamp=NOW,
        idempotency_key="fill-request-1",
    )

    assert retry is order
    assert order.filled_quantity == pytest.approx(4)
    assert len(broker.executions) == 1
    execution = broker.executions[0]
    assert execution.order_id == order.id
    assert execution.quantity == pytest.approx(4)
    assert execution.price == pytest.approx(100)
    assert execution.executed_at == NOW

    with pytest.raises(ValueError, match="reused with different details"):
        broker.fill_order(
            order.id,
            price=101,
            quantity=4,
            timestamp=NOW,
            idempotency_key="fill-request-1",
        )
