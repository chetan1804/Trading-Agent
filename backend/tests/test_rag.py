from app.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient


def test_rag_endpoint_returns_contextual_answer() -> None:
    app = create_app(Settings(enable_trading=False))
    client = TestClient(app)

    response = client.post(
        "/api/ai/rag",
        json={
            "query": "What does management say about demand and guidance?",
            "documents": [
                "Management sees broad-based demand across products and a constructive outlook.",
                "Margins are expected to improve as supply constraints ease.",
                "The company remains focused on disciplined execution and cash generation.",
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["query"] == "What does management say about demand and guidance?"
    assert "answer" in payload
    assert "top_hits" in payload
    assert payload["top_hits"]
