import pandas as pd
import pytest
from trading.data.synthetic import generate_synthetic_ohlcv
from trading.features.feature_pipeline import FeatureConfig, engineer_features


def test_pipeline_builds_indicators_and_preserves_input_bars() -> None:
    source = generate_synthetic_ohlcv(periods=100)
    result = engineer_features(source)

    expected_features = {
        "return_1",
        "log_return_1",
        "return_5",
        "sma_20",
        "ema_50",
        "rsi_14",
        "macd_histogram",
        "bollinger_width_20",
        "atr_14",
        "adx_14",
        "stochastic_k_14",
        "volume_change_1",
        "obv",
        "vwap_20",
        "rolling_volatility_20",
        "hour_utc",
        "day_of_week_utc",
        "month_utc",
    }
    assert expected_features.issubset(result.columns)
    expected_input = source.assign(timestamp=pd.to_datetime(source["timestamp"], utc=True))
    pd.testing.assert_frame_equal(result[source.columns], expected_input)
    assert result["sma_20"].iloc[:19].isna().all()
    assert result["rsi_14"].iloc[:14].isna().all()


def test_future_data_changes_do_not_change_earlier_features() -> None:
    source = generate_synthetic_ohlcv(periods=120)
    baseline = engineer_features(source)
    changed = source.copy()
    changed.loc[80:, ["open", "high", "low", "close"]] *= 3
    changed.loc[80:, "volume"] *= 4
    revised = engineer_features(changed)
    feature_columns = [column for column in baseline if column not in source.columns]

    pd.testing.assert_frame_equal(
        baseline.loc[:79, feature_columns],
        revised.loc[:79, feature_columns],
        check_dtype=False,
    )


def test_features_are_independent_per_symbol() -> None:
    first = generate_synthetic_ohlcv(symbol="AAA", periods=70, seed=1)
    second = generate_synthetic_ohlcv(symbol="BBB", periods=70, seed=2)
    combined = engineer_features(pd.concat([first, second], ignore_index=True))
    standalone = engineer_features(first)
    feature_columns = [column for column in standalone if column not in first.columns]

    pd.testing.assert_frame_equal(
        combined.loc[combined["symbol"] == "AAA", feature_columns].reset_index(drop=True),
        standalone[feature_columns].reset_index(drop=True),
        check_dtype=False,
    )


def test_pipeline_sorts_unsorted_bars_and_rejects_invalid_input() -> None:
    source = generate_synthetic_ohlcv(periods=60).iloc[::-1]
    result = engineer_features(source)
    invalid = source.copy()
    invalid.loc[invalid.index[0], "high"] = invalid.loc[invalid.index[0], "open"] - 1

    assert result["timestamp"].is_monotonic_increasing
    with pytest.raises(ValueError, match="invalid OHLCV"):
        engineer_features(invalid)


def test_feature_config_rejects_invalid_windows() -> None:
    with pytest.raises(ValueError, match="fast MACD"):
        FeatureConfig(macd_fast=30, macd_slow=20)
