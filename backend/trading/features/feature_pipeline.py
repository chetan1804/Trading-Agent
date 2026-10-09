from dataclasses import dataclass

import numpy as np
import pandas as pd

from trading.data.validation import validate_ohlcv
from trading.features.statistical import calculate_return_features, rolling_volatility
from trading.features.technical import (
    average_directional_index,
    average_true_range,
    bollinger_bands,
    exponential_moving_average,
    moving_average_convergence_divergence,
    on_balance_volume,
    relative_strength_index,
    rolling_vwap,
    simple_moving_average,
    stochastic_oscillator,
)


@dataclass(frozen=True)
class FeatureConfig:
    return_windows: tuple[int, ...] = (5, 20)
    sma_windows: tuple[int, ...] = (20, 50)
    ema_windows: tuple[int, ...] = (20, 50)
    rsi_window: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    bollinger_window: int = 20
    atr_window: int = 14
    adx_window: int = 14
    stochastic_window: int = 14
    stochastic_smooth_window: int = 3
    volatility_window: int = 20
    volume_window: int = 20
    vwap_window: int = 20

    def __post_init__(self) -> None:
        windows = (
            *self.return_windows,
            *self.sma_windows,
            *self.ema_windows,
            self.rsi_window,
            self.macd_fast,
            self.macd_slow,
            self.macd_signal,
            self.bollinger_window,
            self.atr_window,
            self.adx_window,
            self.stochastic_window,
            self.stochastic_smooth_window,
            self.volatility_window,
            self.volume_window,
            self.vwap_window,
        )
        if any(window < 1 for window in windows):
            raise ValueError("feature windows must be at least 1")
        if not self.sma_windows or not self.ema_windows:
            raise ValueError("at least one SMA and EMA window is required")
        if len(self.ema_windows) > 1 and self.ema_windows[0] >= self.ema_windows[-1]:
            raise ValueError("EMA windows must be ordered from fastest to slowest")
        if self.macd_fast >= self.macd_slow:
            raise ValueError("fast MACD window must be smaller than slow window")


def engineer_features(
    data: pd.DataFrame,
    config: FeatureConfig | None = None,
) -> pd.DataFrame:
    """Build trailing-window features independently per symbol with no future inputs."""
    settings = config or FeatureConfig()
    report = validate_ohlcv(data, max_abs_close_return=None)
    if report.has_errors:
        codes = sorted({issue.code for issue in report.issues if issue.severity == "error"})
        raise ValueError(f"Cannot engineer features from invalid OHLCV data: {', '.join(codes)}")

    frame = report.data
    if frame["symbol"].astype("string").str.strip().eq("").any():
        raise ValueError("symbol values cannot be blank")
    if (frame["close"] <= 0).any():
        raise ValueError("close prices must be positive to calculate log returns")

    parts = [_engineer_symbol(group, settings) for _, group in frame.groupby("symbol", sort=False)]
    if not parts:
        return frame.copy()
    return (
        pd.concat(parts, ignore_index=True)
        .sort_values(["symbol", "timestamp"], kind="stable")
        .reset_index(drop=True)
    )


def _engineer_symbol(data: pd.DataFrame, config: FeatureConfig) -> pd.DataFrame:
    result = data.copy()
    close = result["close"]
    features = calculate_return_features(close, config.return_windows)

    for window in config.sma_windows:
        average = simple_moving_average(close, window)
        features[f"sma_{window}"] = average
        features[f"sma_distance_{window}"] = close / average - 1
    for window in config.ema_windows:
        average = exponential_moving_average(close, window)
        features[f"ema_{window}"] = average
        features[f"ema_distance_{window}"] = close / average - 1

    if len(config.ema_windows) > 1:
        fast_ema = features[f"ema_{config.ema_windows[0]}"]
        slow_ema = features[f"ema_{config.ema_windows[-1]}"]
        features["trend_direction"] = np.sign(fast_ema - slow_ema)

    features[f"rsi_{config.rsi_window}"] = relative_strength_index(close, config.rsi_window)
    macd_line, macd_signal, macd_histogram = moving_average_convergence_divergence(
        close, config.macd_fast, config.macd_slow, config.macd_signal
    )
    features["macd_line"] = macd_line
    features["macd_signal"] = macd_signal
    features["macd_histogram"] = macd_histogram

    middle, upper, lower, width = bollinger_bands(close, config.bollinger_window)
    features[f"bollinger_mid_{config.bollinger_window}"] = middle
    features[f"bollinger_upper_{config.bollinger_window}"] = upper
    features[f"bollinger_lower_{config.bollinger_window}"] = lower
    features[f"bollinger_width_{config.bollinger_window}"] = width
    features[f"atr_{config.atr_window}"] = average_true_range(
        result["high"], result["low"], close, config.atr_window
    )
    features[f"adx_{config.adx_window}"] = average_directional_index(
        result["high"], result["low"], close, config.adx_window
    )

    stochastic_k, stochastic_d = stochastic_oscillator(
        result["high"],
        result["low"],
        close,
        config.stochastic_window,
        config.stochastic_smooth_window,
    )
    features[f"stochastic_k_{config.stochastic_window}"] = stochastic_k
    features[f"stochastic_d_{config.stochastic_smooth_window}"] = stochastic_d

    features["volume_change_1"] = result["volume"].pct_change(fill_method=None)
    features[f"volume_sma_{config.volume_window}"] = simple_moving_average(
        result["volume"], config.volume_window
    )
    features["obv"] = on_balance_volume(close, result["volume"])
    features[f"vwap_{config.vwap_window}"] = rolling_vwap(
        result["high"],
        result["low"],
        close,
        result["volume"],
        config.vwap_window,
    )
    features[f"rolling_volatility_{config.volatility_window}"] = rolling_volatility(
        features["return_1"], config.volatility_window
    )

    collisions = set(result.columns).intersection(features.columns)
    if collisions:
        collision_names = ", ".join(sorted(collisions))
        raise ValueError(f"Input data already contains feature columns: {collision_names}")
    result = pd.concat([result, features], axis=1)
    result["hour_utc"] = result["timestamp"].dt.hour
    result["day_of_week_utc"] = result["timestamp"].dt.dayofweek
    result["month_utc"] = result["timestamp"].dt.month
    return result
