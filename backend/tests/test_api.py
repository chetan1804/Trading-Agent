from app.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient


def test_health_and_portfolio_api_endpoints_work() -> None:
    app = create_app(Settings(enable_trading=False))
    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    portfolio = client.get("/api/portfolio/summary")
    assert portfolio.status_code == 200
    payload = portfolio.json()
    assert payload["cash"] >= 0
    assert payload["positions"] == {}
    assert payload["total_value"] >= 0
    assert "exposure" in payload


def test_market_data_api_endpoints_work() -> None:
    app = create_app(Settings(enable_trading=False))
    client = TestClient(app)

    quote = client.get("/api/market-data/quote?symbol=DEMO")
    assert quote.status_code == 200
    payload = quote.json()
    assert payload["symbol"] == "DEMO"
    assert payload["last_price"] > 0

    history = client.get("/api/market-data/history?symbol=DEMO&limit=5")
    assert history.status_code == 200
    payload = history.json()
    assert payload["symbol"] == "DEMO"
    assert len(payload["data"]) == 5
    assert payload["data"][0]["close"] > 0


def test_feature_engineering_api_endpoints_work() -> None:
    app = create_app(Settings(enable_trading=False))
    client = TestClient(app)

    response = client.get("/api/features/engineer?symbol=DEMO&limit=20")
    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "DEMO"
    assert payload["count"] == 20
    assert "sma_20" in payload["feature_columns"]
    assert payload["rows"][0]["close"] > 0


def test_strategy_api_endpoints_work() -> None:
    app = create_app(Settings(enable_trading=False))
    client = TestClient(app)

    response = client.get("/api/strategies/generate?symbol=DEMO&limit=40")
    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "DEMO"
    assert payload["count"] == 40
    assert payload["signals"][0]["action"] in {"BUY", "SELL", "HOLD"}
    assert payload["strategy_id"].startswith("moving_average_crossover")


def test_backtesting_api_endpoints_work() -> None:
    app = create_app(Settings(enable_trading=False))
    client = TestClient(app)

    response = client.get("/api/backtests/run?symbol=DEMO&limit=30")
    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "DEMO"
    assert payload["initial_cash"] > 0
    assert payload["ending_equity"] > 0
    assert "metrics" in payload
    assert "total_return" in payload["metrics"]
