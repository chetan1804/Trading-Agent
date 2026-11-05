from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest
from app.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient
from trading.backtesting.costs import TransactionCosts
from trading.backtesting.engine import BacktestConfig, BacktestEngine
from trading.ml.targets import next_period_direction
from trading.ml.trainer import SignalModelTrainer
from trading.strategies.ml_strategy import MLProbabilityStrategy


def test_ml_training_endpoint_returns_model_summary(monkeypatch) -> None:
    from app.repositories.models import ModelRegistryRepository

    async def skip_persistence(self, summary, artifact) -> None:
        return None

    monkeypatch.setattr(ModelRegistryRepository, "save", skip_persistence)
    app = create_app(Settings(app_env="test", enable_trading=False))
    with TestClient(app) as client:
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
    assert payload["feature_baseline"] == {"feature_a": 2.0, "feature_b": 11.0}


def test_ml_probability_strategy_uses_threshold_and_next_bar_execution() -> None:
    values = [index / 10 - 2 for index in range(40)]
    labels = [int(value > 0) for value in values]
    summary, artifact = SignalModelTrainer().train_with_artifact(
        features={"score": values},
        labels=labels,
        train_fraction=0.6,
        validation_fraction=0.2,
    )
    strategy = MLProbabilityStrategy(
        artifact=artifact,
        feature_names=("score",),
        buy_threshold=0.65,
        sell_threshold=0.35,
        model_version=str(summary["model_version"]),
    )
    start = datetime(2024, 1, 1, tzinfo=UTC)
    bars = pd.DataFrame(
        {
            "timestamp": [start + timedelta(days=index) for index in range(3)],
            "symbol": ["DEMO"] * 3,
            "open": [100.0, 100.0, 100.0],
            "high": [101.0, 111.0, 111.0],
            "low": [99.0, 99.0, 99.0],
            "close": [100.0, 110.0, 110.0],
            "volume": [1000] * 3,
            "score": [-1.0, 1.0, 1.0],
        }
    )

    signals = strategy.generate_signals(bars)
    assert [signal.action for signal in signals] == ["SELL", "BUY", "BUY"]
    assert signals[1].confidence >= 0.65

    result = BacktestEngine(
        BacktestConfig(
            initial_cash=1_000,
            costs=TransactionCosts(commission_rate=0, slippage_bps=0, spread_bps=0),
        )
    ).run(bars, strategy)

    assert result.open_position is not None
    assert result.open_position.entry_time == bars.iloc[2]["timestamp"].to_pydatetime()
    assert result.open_position.entry_price == 100.0


def test_ml_probability_strategy_rejects_invalid_thresholds() -> None:
    with pytest.raises(ValueError, match="thresholds"):
        MLProbabilityStrategy(
            artifact=b"model",
            feature_names=("score",),
            buy_threshold=0.4,
            sell_threshold=0.6,
        )


def test_next_period_direction_leaves_final_target_unknown() -> None:
    labels = next_period_direction(pd.Series([100.0, 101.0, 99.0]))

    assert labels.iloc[0] == 1
    assert labels.iloc[1] == 0
    assert pd.isna(labels.iloc[2])
