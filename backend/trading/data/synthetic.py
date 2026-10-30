from datetime import UTC, datetime

import numpy as np
import pandas as pd


def generate_synthetic_ohlcv(
    symbol: str = "RELIANCE.NS",
    periods: int = 500,
    start: datetime | None = None,
    frequency: str = "1h",
    seed: int = 7,
) -> pd.DataFrame:
    """Generate deterministic, explicitly labeled synthetic OHLCV observations."""
    if periods < 1:
        raise ValueError("periods must be at least 1")

    generator = np.random.default_rng(seed)
    log_returns = generator.normal(loc=0.0001, scale=0.008, size=periods)
    close = 100.0 * np.exp(np.cumsum(log_returns))
    open_price = np.concatenate(([100.0], close[:-1]))
    excursion = np.abs(generator.normal(loc=0.002, scale=0.006, size=periods))
    high = np.maximum(open_price, close) * (1.0 + excursion)
    low = np.minimum(open_price, close) * (1.0 - excursion)
    volume = generator.lognormal(mean=7.0, sigma=0.5, size=periods).astype(np.int64)

    first_timestamp = start or datetime(2024, 1, 1, tzinfo=UTC)
    timestamps = pd.date_range(start=first_timestamp, periods=periods, freq=frequency, tz="UTC")
    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "symbol": symbol.upper(),
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "data_source": "synthetic",
        }
    )
