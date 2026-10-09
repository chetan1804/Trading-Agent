import numpy as np
import pandas as pd


def _check_window(window: int) -> None:
    if window < 1:
        raise ValueError("window must be at least 1")


def simple_moving_average(close: pd.Series, window: int) -> pd.Series:
    _check_window(window)
    return close.rolling(window=window, min_periods=window).mean()


def exponential_moving_average(close: pd.Series, span: int) -> pd.Series:
    _check_window(span)
    return close.ewm(span=span, adjust=False, min_periods=span).mean()


def relative_strength_index(close: pd.Series, window: int = 14) -> pd.Series:
    _check_window(window)
    change = close.diff()
    average_gain = (
        change.clip(lower=0).ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    )
    average_loss = (
        -change.clip(upper=0).ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    )
    relative_strength = average_gain / average_loss
    rsi = 100 - 100 / (1 + relative_strength)
    rsi = rsi.mask((average_loss == 0) & (average_gain > 0), 100.0)
    return rsi.mask((average_loss == 0) & (average_gain == 0), 50.0)


def moving_average_convergence_divergence(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    if fast >= slow:
        raise ValueError("fast MACD window must be smaller than slow window")
    line = exponential_moving_average(close, fast) - exponential_moving_average(close, slow)
    signal_line = line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    return line, signal_line, line - signal_line


def bollinger_bands(
    close: pd.Series,
    window: int = 20,
    standard_deviations: float = 2.0,
) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    _check_window(window)
    if standard_deviations <= 0:
        raise ValueError("standard_deviations must be positive")
    middle = simple_moving_average(close, window)
    deviation = close.rolling(window=window, min_periods=window).std(ddof=0)
    upper = middle + standard_deviations * deviation
    lower = middle - standard_deviations * deviation
    width = (upper - lower) / middle
    return middle, upper, lower, width


def average_true_range(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    window: int = 14,
) -> pd.Series:
    _check_window(window)
    previous_close = close.shift(1)
    true_range = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.rolling(window=window, min_periods=window).mean()


def average_directional_index(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    window: int = 14,
) -> pd.Series:
    _check_window(window)
    upward_move = high.diff()
    downward_move = -low.diff()
    positive_move = upward_move.where((upward_move > downward_move) & (upward_move > 0), 0.0)
    negative_move = downward_move.where((downward_move > upward_move) & (downward_move > 0), 0.0)
    atr = average_true_range(high, low, close, window)
    positive_di = (
        100 * positive_move.ewm(alpha=1 / window, adjust=False, min_periods=window).mean() / atr
    )
    negative_di = (
        100 * negative_move.ewm(alpha=1 / window, adjust=False, min_periods=window).mean() / atr
    )
    directional_sum = (positive_di + negative_di).replace(0, np.nan)
    directional_index = 100 * (positive_di - negative_di).abs() / directional_sum
    return directional_index.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()


def stochastic_oscillator(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    window: int = 14,
    smooth_window: int = 3,
) -> tuple[pd.Series, pd.Series]:
    _check_window(window)
    _check_window(smooth_window)
    lowest_low = low.rolling(window=window, min_periods=window).min()
    highest_high = high.rolling(window=window, min_periods=window).max()
    percent_k = 100 * (close - lowest_low) / (highest_high - lowest_low)
    percent_d = percent_k.rolling(window=smooth_window, min_periods=smooth_window).mean()
    return percent_k, percent_d


def on_balance_volume(close: pd.Series, volume: pd.Series) -> pd.Series:
    direction = np.sign(close.diff()).fillna(0)
    return (direction * volume).cumsum()


def rolling_vwap(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
    window: int = 20,
) -> pd.Series:
    _check_window(window)
    typical_price = (high + low + close) / 3
    volume_sum = volume.rolling(window=window, min_periods=window).sum()
    weighted_sum = (typical_price * volume).rolling(window=window, min_periods=window).sum()
    return weighted_sum / volume_sum.replace(0, np.nan)
