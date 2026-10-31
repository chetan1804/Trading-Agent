from trading.model_monitoring.monitor import ModelMonitor


def test_model_monitor_reports_metrics_from_recorded_observations() -> None:
    monitor = ModelMonitor()
    baseline = {"feature_a": 2.0}
    observations = [
        {
            "features": {"feature_a": 3.0},
            "prediction": 1,
            "actual_label": 1,
        },
        {
            "features": {"feature_a": 3.0},
            "prediction": 0,
            "actual_label": 1,
        },
    ]

    report = monitor.evaluate_observations(baseline, observations)

    assert report["status"] == "collecting"
    assert report["observation_count"] == 2
    assert report["labeled_count"] == 2
    assert report["feature_drift"]["feature_a"] == 0.5
    assert report["accuracy"] == 0.5


def test_model_monitor_does_not_invent_metrics_without_observations() -> None:
    report = ModelMonitor().evaluate_observations({}, [])

    assert report["status"] == "unavailable"
    assert report["accuracy"] is None
    assert report["feature_drift"] is None


def test_model_monitor_can_flag_feature_drift_before_outcomes_arrive() -> None:
    observations = [
        {"features": {"feature_a": 2.3}, "prediction": index % 2, "actual_label": None}
        for index in range(ModelMonitor.minimum_observations)
    ]

    report = ModelMonitor().evaluate_observations({"feature_a": 2.0}, observations)

    assert report["status"] == "warning"
    assert report["accuracy"] is None
