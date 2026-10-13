from app.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient


def test_monitoring_overview_endpoint_returns_execution_and_model_status() -> None:
    app = create_app(Settings(enable_trading=False))
    client = TestClient(app)

    response = client.get("/api/monitoring/overview")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "execution" in payload
    assert "model" in payload
    assert "alerts" in payload
