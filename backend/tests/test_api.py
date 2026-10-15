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
