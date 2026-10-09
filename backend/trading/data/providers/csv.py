from datetime import datetime
from pathlib import Path

import pandas as pd

from trading.data.providers.base import MarketQuote


class MarketDataNotFoundError(LookupError):
    """Raised when a provider has no observations for the requested symbol."""


class CsvMarketDataProvider:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def get_historical_data(
        self,
        symbol: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> pd.DataFrame:
        data = pd.read_csv(self.path)
        data.columns = [str(column).strip().lower() for column in data.columns]
        if data.columns.duplicated().any():
            raise ValueError("CSV contains duplicate columns after name normalization")

        required = {"timestamp", "symbol", "open", "high", "low", "close", "volume"}
        missing = required.difference(data.columns)
        if missing:
            raise ValueError(f"CSV is missing required columns: {', '.join(sorted(missing))}")

        matches = data["symbol"].astype("string").str.casefold() == symbol.casefold()
        data = data.loc[matches].copy()
        if start is not None or end is not None:
            timestamps = pd.to_datetime(data["timestamp"], utc=True, errors="raise")
            if start is not None:
                data = data.loc[timestamps >= _as_utc_timestamp(start)]
                timestamps = timestamps.loc[data.index]
            if end is not None:
                data = data.loc[timestamps <= _as_utc_timestamp(end)]
        return data.reset_index(drop=True)

    def get_latest_price(self, symbol: str) -> float:
        data = self.get_historical_data(symbol)
        if data.empty:
            raise MarketDataNotFoundError(f"No market data available for {symbol}")
        timestamps = pd.to_datetime(data["timestamp"], utc=True, errors="raise")
        latest_index = timestamps.idxmax()
        return float(data.loc[latest_index, "close"])

    def get_quote(self, symbol: str) -> MarketQuote:
        data = self.get_historical_data(symbol)
        if data.empty:
            raise MarketDataNotFoundError(f"No market data available for {symbol}")
        timestamps = pd.to_datetime(data["timestamp"], utc=True, errors="raise")
        latest_index = timestamps.idxmax()
        return MarketQuote(
            symbol=str(data.loc[latest_index, "symbol"]),
            timestamp=timestamps.loc[latest_index].to_pydatetime(),
            last_price=float(data.loc[latest_index, "close"]),
        )


def _as_utc_timestamp(value: datetime) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        return timestamp.tz_localize("UTC")
    return timestamp.tz_convert("UTC")
