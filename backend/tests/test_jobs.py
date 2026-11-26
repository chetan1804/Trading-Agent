from app.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient


def test_ai_research_job_runs_and_reports_status() -> None:
    app = create_app(Settings(app_env="test", enable_trading=False))
    with TestClient(app) as client:
        created = client.post(
            "/api/jobs",
            json={
                "type": "ai_research",
                "symbol": "DEMO",
                "market_snapshot": {"price": 100.0, "change_pct": 1.0},
                "news": ["DEMO reports strong demand"],
            },
        )

        assert created.status_code == 200
        job = created.json()
        status = client.get(f"/api/jobs/{job['job_id']}")

    assert status.status_code == 200
    payload = status.json()
    assert payload["status"] == "succeeded"
    assert payload["result"]["symbol"] == "DEMO"


def test_backtest_job_runs_without_external_data() -> None:
    app = create_app(Settings(app_env="test", enable_trading=False))
    with TestClient(app) as client:
        created = client.post(
            "/api/jobs",
            json={
                "type": "backtest",
                "symbol": "DEMO",
                "limit": 120,
                "initial_cash": 50000,
            },
        )
        status = client.get(f"/api/jobs/{created.json()['job_id']}")

    assert created.status_code == 200
    assert status.status_code == 200
    payload = status.json()
    assert payload["status"] == "succeeded"
    assert payload["result"]["data_source"] == "synthetic"
    assert payload["result"]["strategy_id"] == "moving_average"
    assert payload["result"]["trade_count"] >= 0


def test_unknown_job_status_returns_not_found() -> None:
    app = create_app(Settings(app_env="test", enable_trading=False))
    with TestClient(app) as client:
        response = client.get("/api/jobs/missing-job")

    assert response.status_code == 404
