from app.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient


def test_deployment_status_endpoint_returns_runtime_summary() -> None:
    app = create_app(Settings(enable_trading=False))
    with TestClient(app) as client:
        response = client.get("/api/deployment/status")

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ok"
        assert payload["environment"] in {"development", "production", "staging", "test"}
        assert "broker_mode" in payload
        assert "services" in payload
        assert set(payload["services"]) >= {
            "backend",
            "postgres",
            "redis",
            "market_data",
            "broker",
            "model_service",
        }
        assert "docker_ready" in payload
