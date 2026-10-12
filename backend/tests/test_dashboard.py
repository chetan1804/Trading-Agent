from app.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient


def test_dashboard_overview_endpoint_returns_summary() -> None:
    app = create_app(Settings(enable_trading=False))
    client = TestClient(app)

    response = client.get("/api/dashboard/overview")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "portfolio" in payload
    assert "performance" in payload
    assert "execution" in payload
