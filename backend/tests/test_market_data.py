from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest
from trading.data.providers.csv import CsvMarketDataProvider, MarketDataNotFoundError
from trading.data.synthetic import generate_synthetic_ohlcv
from trading.data.validation import validate_ohlcv


def test_synthetic_data_is_reproducible_and_well_formed() -> None:
    first = generate_synthetic_ohlcv(periods=20, seed=11)
    second = generate_synthetic_ohlcv(periods=20, seed=11)

    pd.testing.assert_frame_equal(first, second)
    assert first["data_source"].eq("synthetic").all()
    assert (first["high"] >= first[["open", "close"]].max(axis=1)).all()
    assert (first["low"] <= first[["open", "close"]].min(axis=1)).all()


def test_validation_reports_problems_and_preserves_rows(caplog: pytest.LogCaptureFixture) -> None:
    source = pd.DataFrame(
        {
            "timestamp": ["2024-01-01 02:00", "2024-01-01 01:00", "2024-01-01 01:00"],
            "symbol": ["DEMO", "DEMO", "DEMO"],
            "open": [10, 9, 9],
            "high": [11, 10, 10],
            "low": [9, 8, 8],
            "close": [10, 9, 9],
            "volume": [100, 100, 100],
        }
    )

    report = validate_ohlcv(source, expected_interval="1h")

    assert report.has_errors
    assert len(report.data) == len(source)
    assert report.data["timestamp"].dt.tz is not None
    assert report.data["timestamp"].is_monotonic_increasing
    assert "duplicate_observations" in {issue.code for issue in report.issues}
    assert "market_data_quality_issue" in caplog.text


def test_validation_flags_invalid_ohlc_without_repairing_prices() -> None:
    source = generate_synthetic_ohlcv(periods=3)
    source.loc[1, "high"] = source.loc[1, "open"] - 1

    report = validate_ohlcv(source, max_abs_close_return=None)

    assert "invalid_ohlc" in {issue.code for issue in report.issues}
    assert report.data.loc[1, "high"] == source.loc[1, "high"]


def test_validation_reports_gap_and_outlier() -> None:
    source = pd.DataFrame(
        {
            "timestamp": ["2024-01-01T00:00:00Z", "2024-01-01T03:00:00Z"],
            "symbol": ["DEMO", "DEMO"],
            "open": [10, 40],
            "high": [11, 41],
            "low": [9, 39],
            "close": [10, 40],
            "volume": [1, 1],
        }
    )

    report = validate_ohlcv(source, expected_interval="1h", max_abs_close_return=1.0)

    assert {issue.code for issue in report.issues} == {"data_gaps", "outlier_price_moves"}


def test_csv_provider_filters_and_returns_latest_quote(tmp_path: Path) -> None:
    data = generate_synthetic_ohlcv(symbol="DEMO", periods=4)
    data.to_csv(tmp_path / "prices.csv", index=False)
    provider = CsvMarketDataProvider(tmp_path / "prices.csv")

    result = provider.get_historical_data(
        "demo",
        start=datetime(2024, 1, 1, 1, tzinfo=UTC),
        end=datetime(2024, 1, 1, 2, tzinfo=UTC),
    )
    quote = provider.get_quote("DEMO")

    assert len(result) == 2
    assert provider.get_latest_price("DEMO") == quote.last_price
    assert quote.bid is None and quote.ask is None


def test_csv_provider_raises_for_unknown_symbol(tmp_path: Path) -> None:
    generate_synthetic_ohlcv(periods=2).to_csv(tmp_path / "prices.csv", index=False)
    provider = CsvMarketDataProvider(tmp_path / "prices.csv")

    with pytest.raises(MarketDataNotFoundError):
        provider.get_latest_price("UNKNOWN")
