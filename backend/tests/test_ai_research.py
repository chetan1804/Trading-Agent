from app.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient


def test_ai_research_endpoint_returns_structured_summary() -> None:
    app = create_app(Settings(enable_trading=False))
    client = TestClient(app)

    response = client.post(
        "/api/ai/research",
        json={
            "symbol": "AAPL",
            "market_snapshot": {"price": 214.42, "change_pct": 1.8, "volume": 3200000},
            "news": [
                "AAPL reports strong product demand and healthy cash generation.",
                "Analysts point to improving margins in the next quarter.",
            ],
            "documents": [
                "Company guidance remains constructive with broad-based demand.",
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AAPL"
    assert "summary" in payload
    assert payload["provider"] in {"local", "disabled"}
    assert "risks" in payload
    assert "highlights" in payload
