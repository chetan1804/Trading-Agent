from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score


class SignalModelTrainer:
    def train(
        self,
        *,
        features: dict[str, Sequence[float]],
        labels: Sequence[int],
    ) -> dict[str, object]:
        if not features:
            raise ValueError("features must not be empty")
        if not labels:
            raise ValueError("labels must not be empty")

        feature_names = list(features)
        rows = len(next(iter(features.values())))
        if any(len(values) != rows for values in features.values()):
            raise ValueError("all feature columns must have the same length")
        if len(labels) != rows:
            raise ValueError("labels length must match feature row count")

        x = np.column_stack([np.asarray(features[name], dtype=float) for name in feature_names])
        y = np.asarray(labels, dtype=int)

        model = LogisticRegression(max_iter=1000)
        model.fit(x, y)
        predictions = model.predict(x)

        metrics = {
            "accuracy": float(accuracy_score(y, predictions)),
            "precision": float(precision_score(y, predictions, zero_division=0)),
            "recall": float(recall_score(y, predictions, zero_division=0)),
            "f1_score": float(f1_score(y, predictions, zero_division=0)),
        }

        return {
            "status": "ok",
            "model_type": "logistic_regression",
            "feature_names": feature_names,
            "metrics": metrics,
            "classes": model.classes_.tolist(),
        }
