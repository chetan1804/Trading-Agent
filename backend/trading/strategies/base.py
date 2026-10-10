from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol

import pandas as pd

SignalAction = Literal["BUY", "SELL", "HOLD"]


@dataclass(frozen=True)
class TradingSignal:
    symbol: str
    timestamp: datetime
    action: SignalAction
    confidence: float
    reason: str
    strategy_id: str


class Strategy(Protocol):
    @property
    def strategy_id(self) -> str: ...

    def generate_signals(self, market_data: pd.DataFrame) -> list[TradingSignal]:
        """Return timestamped signals; execution is handled separately."""
        ...
