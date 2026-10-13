from app.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient


def test_agent_orchestration_endpoint_returns_plan() -> None:
    app = create_app(Settings(enable_trading=False))
    client = TestClient(app)

    response = client.post(
        "/api/agents/run",
        json={
            "symbol": "NVDA",
            "objective": "Assess trend strength and note risks before a new position.",
            "market_snapshot": {"price": 134.2, "change_pct": 2.4, "volume": 51000000},
            "news": [
                "Chip demand remains elevated and guidance is constructive.",
                "Supply constraints are easing but execution remains uneven.",
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "NVDA"
    assert payload["status"] == "ok"
    assert "plan" in payload
    assert "actions" in payload
    assert "agent" in payload
