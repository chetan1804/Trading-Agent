from dataclasses import dataclass

import pandas as pd

from trading.strategies.base import TradingSignal


@dataclass(frozen=True)
class BuyAndHoldStrategy:
    @property
    def strategy_id(self) -> str:
        return "buy_and_hold"

    def generate_signals(self, market_data: pd.DataFrame) -> list[TradingSignal]:
        required_columns = {"timestamp", "symbol"}
        missing_columns = sorted(required_columns.difference(market_data.columns))
        if missing_columns:
            raise ValueError(f"Missing strategy input columns: {', '.join(missing_columns)}")
        if market_data.empty:
            return []
        data = market_data.copy()
        data["timestamp"] = pd.to_datetime(data["timestamp"], utc=True, errors="coerce")
        if data["timestamp"].isna().any():
            raise ValueError("Strategy input contains invalid timestamps")
        data = data.sort_values("timestamp", kind="stable")
        first = data.iloc[0]
        return [
            TradingSignal(
                symbol=str(first["symbol"]),
                timestamp=first["timestamp"].to_pydatetime(),
                action="BUY",
                confidence=1.0,
                reason="Buy once on the first observed bar and hold through the test window.",
                strategy_id=self.strategy_id,
            )
        ]
