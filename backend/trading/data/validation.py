import logging
from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)
REQUIRED_COLUMNS = ("timestamp", "symbol", "open", "high", "low", "close", "volume")
NUMERIC_COLUMNS = ("open", "high", "low", "close", "volume")


@dataclass(frozen=True)
class DataQualityIssue:
    code: str
    severity: Literal["error", "warning"]
    message: str
    row_count: int


@dataclass
class DataQualityReport:
    data: pd.DataFrame
    issues: tuple[DataQualityIssue, ...]

    @property
    def has_errors(self) -> bool:
        return any(issue.severity == "error" for issue in self.issues)


def validate_ohlcv(
    data: pd.DataFrame,
    expected_interval: str | pd.Timedelta | None = None,
    max_abs_close_return: float | None = 1.0,
) -> DataQualityReport:
    """Report OHLCV quality issues and normalize timestamps/order without dropping rows."""
    if max_abs_close_return is not None and max_abs_close_return <= 0:
        raise ValueError("max_abs_close_return must be positive or None")
    interval = pd.to_timedelta(expected_interval) if expected_interval is not None else None
    if interval is not None and interval <= pd.Timedelta(0):
        raise ValueError("expected_interval must be positive")

    normalized = data.copy(deep=True)
    normalized.columns = [str(column).strip().lower() for column in normalized.columns]
    issues: list[DataQualityIssue] = []

    def record(
        code: str,
        severity: Literal["error", "warning"],
        message: str,
        row_count: int,
    ) -> None:
        issue = DataQualityIssue(code, severity, message, row_count)
        issues.append(issue)
        log_level = logging.ERROR if severity == "error" else logging.WARNING
        logger.log(log_level, "market_data_quality_issue %s rows=%d: %s", code, row_count, message)

    duplicated_columns = normalized.columns[normalized.columns.duplicated()].unique().tolist()
    if duplicated_columns:
        record(
            "duplicate_columns",
            "error",
            "Column names are duplicated after normalization",
            len(duplicated_columns),
        )
        return DataQualityReport(normalized, tuple(issues))

    missing_columns = sorted(set(REQUIRED_COLUMNS).difference(normalized.columns))
    if missing_columns:
        record(
            "missing_columns", "error", f"Missing required columns: {', '.join(missing_columns)}", 0
        )
        return DataQualityReport(normalized, tuple(issues))

    source_timestamps = normalized["timestamp"]
    parsed_timestamps = pd.to_datetime(source_timestamps, utc=True, errors="coerce")
    missing_timestamps = int(source_timestamps.isna().sum())
    invalid_timestamps = int((source_timestamps.notna() & parsed_timestamps.isna()).sum())
    if missing_timestamps:
        record("missing_timestamps", "error", "Rows contain missing timestamps", missing_timestamps)
    if invalid_timestamps:
        record(
            "invalid_timestamps", "error", "Rows contain unparseable timestamps", invalid_timestamps
        )
    normalized["timestamp"] = parsed_timestamps

    for column in ("symbol", *NUMERIC_COLUMNS):
        missing_count = int(normalized[column].isna().sum())
        if missing_count:
            record(
                "missing_values", "error", f"Column {column} contains missing values", missing_count
            )

    for column in NUMERIC_COLUMNS:
        original = normalized[column]
        converted = pd.to_numeric(original, errors="coerce")
        invalid_count = int((original.notna() & converted.isna()).sum())
        if invalid_count:
            record(
                "invalid_numeric_values",
                "error",
                f"Column {column} contains non-numeric values",
                invalid_count,
            )
        non_finite = converted.notna() & ~np.isfinite(converted)
        non_finite_count = int(non_finite.sum())
        if non_finite_count:
            record(
                "non_finite_values",
                "error",
                f"Column {column} contains non-finite values",
                non_finite_count,
            )
        normalized[column] = converted

    complete_ohlc = normalized[["open", "high", "low", "close"]].notna().all(axis=1)
    invalid_ohlc = complete_ohlc & (
        (normalized["high"] < normalized[["open", "close"]].max(axis=1))
        | (normalized["low"] > normalized[["open", "close"]].min(axis=1))
        | (normalized["high"] < normalized["low"])
    )
    invalid_ohlc_count = int(invalid_ohlc.sum())
    if invalid_ohlc_count:
        record(
            "invalid_ohlc", "error", "Rows violate OHLC high/low constraints", invalid_ohlc_count
        )

    negative_volume_count = int((normalized["volume"].notna() & (normalized["volume"] < 0)).sum())
    if negative_volume_count:
        record("negative_volume", "error", "Rows contain negative volume", negative_volume_count)

    valid_key = normalized["symbol"].notna() & normalized["timestamp"].notna()
    duplicate_count = int(
        normalized.loc[valid_key].duplicated(subset=["symbol", "timestamp"], keep=False).sum()
    )
    if duplicate_count:
        record(
            "duplicate_observations",
            "error",
            "Symbol/timestamp pairs are duplicated",
            duplicate_count,
        )

    normalized = normalized.sort_values(["symbol", "timestamp"], kind="stable", na_position="last")
    if interval is not None:
        differences = normalized.loc[valid_key].groupby("symbol", sort=False)["timestamp"].diff()
        gaps = differences[differences > interval]
        missing_periods = sum(max(int(gap / interval) - 1, 1) for gap in gaps)
        if missing_periods:
            record(
                "data_gaps",
                "warning",
                "Expected intervals are missing between observations",
                missing_periods,
            )

    if max_abs_close_return is not None:
        close_returns = normalized.groupby("symbol", dropna=True, sort=False)["close"].pct_change(
            fill_method=None
        )
        outlier_count = int((close_returns.abs() > max_abs_close_return).sum())
        if outlier_count:
            record(
                "outlier_price_moves",
                "warning",
                "Close-to-close return exceeds configured threshold",
                outlier_count,
            )

    return DataQualityReport(normalized, tuple(issues))
