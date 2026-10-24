from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from datetime import UTC, datetime

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


class SignalModelTrainer:
    def train(
        self,
        *,
        features: dict[str, Sequence[float]],
        labels: Sequence[int],
        train_fraction: float = 0.6,
        validation_fraction: float = 0.2,
    ) -> dict[str, object]:
        if not features:
            raise ValueError("features must not be empty")
        if not labels:
            raise ValueError("labels must not be empty")
        if not 0 < train_fraction < 1:
            raise ValueError("train_fraction must be between 0 and 1")
        if not 0 < validation_fraction < 1 or train_fraction + validation_fraction >= 1:
            raise ValueError("train and validation fractions must leave rows for testing")

        feature_names = list(features)
        rows = len(next(iter(features.values())))
        if any(len(values) != rows for values in features.values()):
            raise ValueError("all feature columns must have the same length")
        if len(labels) != rows:
            raise ValueError("labels length must match feature row count")

        x = np.column_stack([np.asarray(features[name], dtype=float) for name in feature_names])
        if not np.isfinite(x).all():
            raise ValueError("features must contain only finite values")
        raw_labels = np.asarray(labels)
        if not np.isin(raw_labels, [0, 1]).all():
            raise ValueError("labels must be binary values 0 or 1")
        y = raw_labels.astype(int)

        train_end = int(rows * train_fraction)
        validation_end = train_end + int(rows * validation_fraction)
        if train_end < 2 or validation_end <= train_end or validation_end >= rows:
            raise ValueError("not enough rows for chronological train/validation/test splits")
        x_train, y_train = x[:train_end], y[:train_end]
        x_validation, y_validation = x[train_end:validation_end], y[train_end:validation_end]
        x_test, y_test = x[validation_end:], y[validation_end:]
        if np.unique(y_train).size < 2:
            raise ValueError("training labels must contain both binary classes")

        model = Pipeline(
            [
                ("scaler", StandardScaler()),
                ("classifier", LogisticRegression(max_iter=1000)),
            ]
        )
        model.fit(x_train, y_train)
        validation_predictions = model.predict(x_validation)
        test_predictions = model.predict(x_test)

        def calculate_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
            return {
                "accuracy": float(accuracy_score(actual, predicted)),
                "precision": float(precision_score(actual, predicted, zero_division=0)),
                "recall": float(recall_score(actual, predicted, zero_division=0)),
                "f1_score": float(f1_score(actual, predicted, zero_division=0)),
            }

        dataset_digest = hashlib.sha256(
            json.dumps(
                {
                    "features": feature_names,
                    "x": x.tolist(),
                    "y": y.tolist(),
                },
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()
        dataset_version = f"sha256:{dataset_digest}"
        model_signature = (
            f"{dataset_digest}:logistic-regression:1000:standard-scaler:{train_fraction}:"
            f"{validation_fraction}"
        )
        model_digest = hashlib.sha256(model_signature.encode("utf-8")).hexdigest()
        model_version = f"logistic-regression-{model_digest[:12]}"
        classifier = model.named_steps["classifier"]

        return {
            "status": "ok",
            "model_type": "logistic_regression",
            "model_version": model_version,
            "dataset_version": dataset_version,
            "training_date": datetime.now(UTC).isoformat(),
            "feature_names": feature_names,
            "hyperparameters": {
                "scaler": "StandardScaler",
                "classifier": "LogisticRegression",
                "max_iter": 1000,
                "train_fraction": train_fraction,
                "validation_fraction": validation_fraction,
            },
            "metrics": calculate_metrics(y_test, test_predictions),
            "validation_metrics": calculate_metrics(y_validation, validation_predictions),
            "split_rows": {
                "train": int(len(y_train)),
                "validation": int(len(y_validation)),
                "test": int(len(y_test)),
            },
            "classes": classifier.classes_.tolist(),
        }
