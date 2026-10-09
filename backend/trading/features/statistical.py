import numpy as np
import pandas as pd


def calculate_return_features(
    close: pd.Series,
    windows: tuple[int, ...] = (5, 20),
) -> pd.DataFrame:
    features = pd.DataFrame(index=close.index)
    features["return_1"] = close.pct_change(fill_method=None)
    features["log_return_1"] = np.log(close).diff()
    features["price_change_1"] = close.diff()
    for window in windows:
        if window < 1:
            raise ValueError("return windows must be at least 1")
        features[f"return_{window}"] = close.pct_change(periods=window, fill_method=None)
    return features


def rolling_volatility(returns: pd.Series, window: int) -> pd.Series:
    if window < 1:
        raise ValueError("window must be at least 1")
    return returns.rolling(window=window, min_periods=window).std(ddof=0)
