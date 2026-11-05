import numpy as np
import pandas as pd


def next_period_direction(close: pd.Series) -> pd.Series:
    """Label each bar by whether the following bar's close is higher.

    The final row has no known target and remains missing. The caller must
    ensure each training label's next close is available before model fitting.
    """
    prices = pd.to_numeric(close, errors="coerce")
    if not np.isfinite(prices.to_numpy(dtype=float)).all() or prices.le(0).any():
        raise ValueError("close prices must be finite and positive")
    next_close = prices.shift(-1)
    labels = (next_close > prices).astype("float64")
    labels.loc[next_close.isna()] = float("nan")
    return labels
