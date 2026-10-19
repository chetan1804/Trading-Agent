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


def test_risk_api_evaluation_endpoints_work() -> None:
    app = create_app(Settings(enable_trading=False))
    client = TestClient(app)

    response = client.post(
        "/api/risk/evaluate",
        json={
            "enabled": True,
            "symbol": "DEMO",
            "side": "BUY",
            "entry_price": 100,
            "stop_loss_price": 95,
            "timestamp": "2024-01-02T00:00:00Z",
            "account": {"equity": 100000, "available_cash": 100000},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["approved"] is True
    assert payload["quantity"] > 0
    assert payload["capital_required"] > 0


def test_portfolio_api_snapshot_endpoint_works() -> None:
    app = create_app(Settings(enable_trading=False))
    client = TestClient(app)

    response = client.get("/api/portfolio/snapshot")
    assert response.status_code == 200
    payload = response.json()
    assert payload["cash"] >= 0
    assert payload["positions"] == {}
    assert payload["total_value"] >= 0
    assert "exposure" in payload


def test_monitoring_api_overview_endpoint_works() -> None:
    app = create_app(Settings(enable_trading=False))
    client = TestClient(app)

    response = client.get("/api/monitoring/overview")
    assert response.status_code == 200
    payload = response.json()
    assert "execution" in payload
    assert "model" in payload
    assert payload["execution"]["open_orders"] >= 0
    assert payload["model"]["status"] in {"healthy", "warning", "degraded"}


def test_paper_trading_order_api_endpoints_work() -> None:
    app = create_app(Settings(enable_trading=False))
    client = TestClient(app)

    create_response = client.post(
        "/api/paper-trading/orders",
        json={"symbol": "DEMO", "side": "BUY", "quantity": 5, "limit_price": 100.0},
    )
    assert create_response.status_code == 200
    payload = create_response.json()
    assert payload["symbol"] == "DEMO"
    assert payload["status"] in {"NEW", "OPEN"}
    assert payload["quantity"] == 5

    list_response = client.get("/api/paper-trading/orders")
    assert list_response.status_code == 200
    listed = list_response.json()
    assert listed["count"] >= 1
    assert listed["orders"][0]["symbol"] == "DEMO"


def test_ai_sentiment_api_endpoint_works() -> None:
    app = create_app(Settings(enable_trading=False))
    client = TestClient(app)

    response = client.post(
        "/api/ai/sentiment",
        json={
            "symbol": "DEMO",
            "headlines": [
                "Earnings beat expectations and management raised guidance.",
                "Analysts remain optimistic as demand expands globally.",
            ],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "DEMO"
    assert payload["sentiment"] in {"bullish", "neutral", "bearish"}
    assert payload["score"] >= -1.0
    assert payload["score"] <= 1.0


def test_agent_run_api_includes_sentiment_context() -> None:
    app = create_app(Settings(enable_trading=False))
    client = TestClient(app)

    response = client.post(
        "/api/agents/run",
        json={
            "symbol": "DEMO",
            "objective": "Assess near-term direction.",
            "market_snapshot": {"price": 101.25, "change_pct": 1.5, "volume": 250000},
            "news": [
                "Revenue expanded strongly and management raised full-year guidance.",
            ],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "DEMO"
    assert payload["status"] == "ok"
    assert payload["sentiment"]["sentiment"] in {"bullish", "neutral", "bearish"}
    assert payload["signal"]["trend"] in {"bullish", "neutral", "bearish"}


def test_broker_status_api_endpoint_works() -> None:
    app = create_app(Settings(enable_trading=False))
    client = TestClient(app)

    response = client.get("/api/broker/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["mode"] in {"paper", "live"}
    assert payload["paper_enabled"] is True
    assert payload["live_enabled"] is False


def test_market_data_news_endpoint_works() -> None:
    app = create_app(Settings(enable_trading=False))
    client = TestClient(app)

    response = client.get("/api/market-data/news?symbol=DEMO&limit=3")
    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "DEMO"
    assert payload["count"] == 3
    assert payload["items"][0]["headline"]
    assert payload["items"][0]["sentiment"] in {"bullish", "neutral", "bearish"}


def test_market_data_validation_endpoint_works() -> None:
    app = create_app(Settings(enable_trading=False))
    client = TestClient(app)

    response = client.get("/api/market-data/validate?symbol=DEMO&limit=20")
    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "DEMO"
    assert payload["valid"] is True
    assert payload["rows"] == 20
    assert payload["null_count"] == 0
    assert payload["issues"] == []


def test_market_data_ingest_endpoint_works() -> None:
    app = create_app(Settings(enable_trading=False))
    client = TestClient(app)

    response = client.post(
        "/api/market-data/ingest",
        json={
            "symbol": "DEMO",
            "bars": [
                {"timestamp": "2024-01-01T00:00:00Z", "open": 99.0, "high": 101.0, "low": 98.5, "close": 100.5, "volume": 1200},
                {"timestamp": "2024-01-02T00:00:00Z", "open": 100.5, "high": 102.0, "low": 99.0, "close": 101.25, "volume": 1300},
            ],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["symbol"] == "DEMO"
    assert payload["stored"] == 2


def test_market_data_store_retrieval_endpoint_works() -> None:
    app = create_app(Settings(enable_trading=False))
    client = TestClient(app)

    client.post(
        "/api/market-data/ingest",
        json={
            "symbol": "DEMO",
            "bars": [
                {"timestamp": "2024-01-03T00:00:00Z", "open": 101.0, "high": 103.0, "low": 100.0, "close": 102.0, "volume": 1400},
                {"timestamp": "2024-01-04T00:00:00Z", "open": 102.0, "high": 104.0, "low": 101.0, "close": 103.0, "volume": 1500},
            ],
        },
    )

    response = client.get("/api/market-data/stored?symbol=DEMO")
    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "DEMO"
    assert payload["count"] == 2
    assert payload["data"][0]["close"] > 0


def test_performance_summary_api_endpoint_works() -> None:
    app = create_app(Settings(enable_trading=False))
    client = TestClient(app)

    response = client.get("/api/performance/summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["total_return"] >= -1.0
    assert payload["final_equity"] > 0
    assert payload["trade_count"] >= 0
