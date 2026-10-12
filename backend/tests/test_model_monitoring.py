import pandas as pd
from trading.model_monitoring.monitor import ModelMonitor


def test_model_monitor_tracks_drift_and_signal_quality() -> None:
    baseline = pd.DataFrame(
        {
            "feature_a": [1.0, 2.0, 3.0, 4.0],
            "feature_b": [10.0, 12.0, 14.0, 16.0],
            "label": [1, 0, 1, 0],
        }
    )
    live = pd.DataFrame(
        {
            "feature_a": [1.5, 2.5, 3.5, 4.5],
            "feature_b": [11.0, 13.0, 15.0, 17.0],
            "label": [1, 1, 0, 0],
        }
    )

    monitor = ModelMonitor()
    report = monitor.evaluate(baseline, live)

    assert report["feature_drift"]["feature_a"] > 0
    assert report["feature_drift"]["feature_b"] > 0
    assert report["accuracy"] > 0
    assert report["precision"] >= 0
    assert report["recall"] >= 0
    assert report["status"] in {"healthy", "warning", "critical"}
