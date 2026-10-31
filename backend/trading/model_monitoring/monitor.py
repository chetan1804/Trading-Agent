from __future__ import annotations

from sklearn.metrics import accuracy_score, precision_score, recall_score


class ModelMonitor:
    minimum_observations = 20

    def evaluate_observations(
        self,
        baseline_means: dict[str, float],
        observations: list[dict[str, object]],
    ) -> dict[str, object]:
        if not observations:
            return {
                "status": "unavailable",
                "reason": "No prediction observations have been recorded.",
                "observation_count": 0,
                "labeled_count": 0,
                "feature_drift": None,
                "accuracy": None,
                "precision": None,
                "recall": None,
            }

        if len(observations) < self.minimum_observations:
            status = "collecting"
        else:
            status = "healthy"

        feature_drift: dict[str, float] = {}
        features = [row["features"] for row in observations]
        for feature, baseline_mean in baseline_means.items():
            live_values = [float(row[feature]) for row in features if feature in row]
            if live_values:
                live_mean = sum(live_values) / len(live_values)
                feature_drift[feature] = abs(live_mean - baseline_mean) / max(
                    abs(baseline_mean), 1e-9
                )

        max_drift = max(feature_drift.values(), default=0.0)
        if len(observations) >= self.minimum_observations:
            if max_drift > 0.25:
                status = "critical"
            elif max_drift > 0.1:
                status = "warning"

        labeled = [row for row in observations if row["actual_label"] is not None]
        metrics: dict[str, float | None] = {
            "accuracy": None,
            "precision": None,
            "recall": None,
        }
        if labeled:
            actual = [int(row["actual_label"]) for row in labeled]
            predicted = [int(row["prediction"]) for row in labeled]
            metrics = {
                "accuracy": float(accuracy_score(actual, predicted)),
                "precision": float(precision_score(actual, predicted, zero_division=0)),
                "recall": float(recall_score(actual, predicted, zero_division=0)),
            }
            if len(labeled) >= self.minimum_observations:
                if metrics["accuracy"] < 0.6:
                    status = "critical"
                elif metrics["accuracy"] < 0.75 and status == "healthy":
                    status = "warning"

        return {
            "status": status,
            "observation_count": len(observations),
            "labeled_count": len(labeled),
            "feature_drift": feature_drift or None,
            **metrics,
        }
