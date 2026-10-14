from app.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient


def test_ml_training_endpoint_returns_model_summary() -> None:
    app = create_app(Settings(enable_trading=False))
    client = TestClient(app)

    response = client.post(
        "/api/ml/train",
        json={
            "features": {
                "feature_a": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
                "feature_b": [10.0, 11.0, 12.0, 13.0, 14.0, 15.0],
            },
            "labels": [0, 0, 1, 1, 1, 1],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["model_type"] == "logistic_regression"
    assert "metrics" in payload
    assert payload["metrics"]["accuracy"] >= 0.0
    assert payload["metrics"]["f1_score"] >= 0.0
