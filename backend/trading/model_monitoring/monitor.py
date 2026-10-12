from __future__ import annotations

from collections.abc import Iterable

import pandas as pd


class ModelMonitor:
    def evaluate(self, baseline: pd.DataFrame, live: pd.DataFrame) -> dict[str, object]:
        feature_columns = [col for col in baseline.columns if col != "label"]
        if not feature_columns:
            raise ValueError("baseline must include feature columns")

        drift: dict[str, float] = {}
        for feature in feature_columns:
            baseline_mean = float(baseline[feature].mean())
            live_mean = float(live[feature].mean())
            drift[feature] = abs(live_mean - baseline_mean) / max(abs(baseline_mean), 1e-9)

        predictions = self._predict(live)
        labels = live["label"].astype(int).tolist()
        accuracy = self._accuracy(labels, predictions)
        precision = self._precision(labels, predictions)
        recall = self._recall(labels, predictions)

        if max(drift.values(), default=0.0) > 0.25 or accuracy < 0.6:
            status = "critical"
        elif max(drift.values(), default=0.0) > 0.1 or accuracy < 0.75:
            status = "warning"
        else:
            status = "healthy"

        return {
            "feature_drift": drift,
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "status": status,
        }

    def _predict(self, frame: pd.DataFrame) -> list[int]:
        feature_columns = [col for col in frame.columns if col != "label"]
        predictions: list[int] = []
        for _, row in frame.iterrows():
            score = sum(float(row[col]) for col in feature_columns)
            predictions.append(1 if score >= 0 else 0)
        return predictions

    @staticmethod
    def _accuracy(labels: Iterable[int], predictions: Iterable[int]) -> float:
        labels_list = list(labels)
        prediction_list = list(predictions)
        if not labels_list:
            return 0.0
        matches = sum(
            int(label == prediction)
            for label, prediction in zip(labels_list, prediction_list, strict=False)
        )
        return matches / len(labels_list)

    @staticmethod
    def _precision(labels: Iterable[int], predictions: Iterable[int]) -> float:
        labels_list = list(labels)
        prediction_list = list(predictions)
        if not prediction_list:
            return 0.0
        positives = sum(int(pred == 1) for pred in prediction_list)
        if positives == 0:
            return 0.0
        return (
            sum(
                int(label == 1 and pred == 1)
                for label, pred in zip(labels_list, prediction_list, strict=False)
            )
            / positives
        )

    @staticmethod
    def _recall(labels: Iterable[int], predictions: Iterable[int]) -> float:
        labels_list = list(labels)
        prediction_list = list(predictions)
        actual_positives = sum(int(label == 1) for label in labels_list)
        if actual_positives == 0:
            return 0.0
        return (
            sum(
                int(label == 1 and pred == 1)
                for label, pred in zip(labels_list, prediction_list, strict=False)
            )
            / actual_positives
        )
