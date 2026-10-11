import pytest
from trading.broker.paper_broker import PaperBroker
from trading.portfolio.manager import PortfolioManager


def test_portfolio_tracks_cash_positions_and_pnl() -> None:
    broker = PaperBroker(initial_cash=100_000.0, slippage_bps=0.0)
    order = broker.create_order(symbol="AAPL", side="BUY", quantity=10, limit_price=100.0)
    broker.submit_order(order, market_price=100.0)
    broker.fill_order(order.id, price=100.0, quantity=10)

    manager = PortfolioManager.from_broker(broker)
    manager.update_market_prices({"AAPL": 110.0})

    assert manager.cash == pytest.approx(98_999.5)
    assert manager.positions["AAPL"] == pytest.approx(10.0)
    assert manager.unrealized_pnl == pytest.approx(100.0)
    assert manager.total_value == pytest.approx(100_099.5)
    assert manager.exposure == pytest.approx(1_100.0)


def test_portfolio_tracks_realized_pnl_on_sell() -> None:
    broker = PaperBroker(initial_cash=50_000.0, slippage_bps=0.0)
    buy = broker.create_order(symbol="MSFT", side="BUY", quantity=5, limit_price=50.0)
    broker.submit_order(buy, market_price=50.0)
    broker.fill_order(buy.id, price=50.0, quantity=5)

    sell = broker.create_order(symbol="MSFT", side="SELL", quantity=2, limit_price=60.0)
    broker.submit_order(sell, market_price=60.0)
    broker.fill_order(sell.id, price=60.0, quantity=2)

    manager = PortfolioManager.from_broker(broker)
    manager.update_market_prices({"MSFT": 58.0})

    assert manager.positions["MSFT"] == pytest.approx(3.0)
    assert manager.realized_pnl == pytest.approx(20.0)
    assert manager.unrealized_pnl == pytest.approx(24.0)
