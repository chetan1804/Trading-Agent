from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

import pandas as pd


@dataclass(frozen=True)
class MarketQuote:
    symbol: str
    timestamp: datetime
    last_price: float
    bid: float | None = None
    ask: float | None = None


class MarketDataProvider(Protocol):
    def get_historical_data(
        self,
        symbol: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> pd.DataFrame: ...

    def get_latest_price(self, symbol: str) -> float:
        """Return the most recent close for a symbol."""
        ...

    def get_quote(self, symbol: str) -> MarketQuote:
        """Return the latest available quote; unavailable fields remain None."""
        ...


class StreamingMarketDataProvider(MarketDataProvider, Protocol):
    def subscribe_market_data(self, symbol: str) -> AsyncIterator[MarketQuote]:
        """Stream quotes when the underlying provider supports real-time data."""
        ...
