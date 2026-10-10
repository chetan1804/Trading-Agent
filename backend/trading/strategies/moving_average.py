from dataclasses import dataclass

import pandas as pd

from trading.strategies.base import SignalAction, TradingSignal


@dataclass(frozen=True)
class MovingAverageCrossoverStrategy:
    fast_window: int = 20
    slow_window: int = 50

    def __post_init__(self) -> None:
        if self.fast_window < 1 or self.slow_window < 1:
            raise ValueError("moving-average windows must be at least 1")
        if self.fast_window >= self.slow_window:
            raise ValueError("fast moving-average window must be smaller than slow window")

    @property
    def strategy_id(self) -> str:
        return f"moving_average_crossover_{self.fast_window}_{self.slow_window}"

    def generate_signals(self, market_data: pd.DataFrame) -> list[TradingSignal]:
        fast_column = f"sma_{self.fast_window}"
        slow_column = f"sma_{self.slow_window}"
        required_columns = {"timestamp", "symbol", fast_column, slow_column}
        missing_columns = sorted(required_columns.difference(market_data.columns))
        if missing_columns:
            raise ValueError(f"Missing strategy input columns: {', '.join(missing_columns)}")

        data = market_data.copy()
        data["timestamp"] = pd.to_datetime(data["timestamp"], utc=True, errors="coerce")
        if data["timestamp"].isna().any():
            raise ValueError("Strategy input contains invalid timestamps")
        data[fast_column] = pd.to_numeric(data[fast_column], errors="coerce")
        data[slow_column] = pd.to_numeric(data[slow_column], errors="coerce")
        data = data.sort_values(["symbol", "timestamp"], kind="stable")

        signals: list[TradingSignal] = []
        for symbol, group in data.groupby("symbol", sort=False):
            previous_fast: float | None = None
            previous_slow: float | None = None
            for row in group.itertuples(index=False):
                current_fast = getattr(row, fast_column)
                current_slow = getattr(row, slow_column)
                action: SignalAction = "HOLD"
                reason = "No moving-average crossover."

                values_are_valid = pd.notna(current_fast) and pd.notna(current_slow)
                previous_values_are_valid = (
                    previous_fast is not None
                    and previous_slow is not None
                    and pd.notna(previous_fast)
                    and pd.notna(previous_slow)
                )
                if values_are_valid and previous_values_are_valid:
                    if previous_fast <= previous_slow and current_fast > current_slow:
                        action = "BUY"
                        reason = (
                            f"SMA {self.fast_window} crossed above SMA {self.slow_window}; "
                            "evaluate execution no earlier than the next bar."
                        )
                    elif previous_fast >= previous_slow and current_fast < current_slow:
                        action = "SELL"
                        reason = (
                            f"SMA {self.fast_window} crossed below SMA {self.slow_window}; "
                            "evaluate execution no earlier than the next bar."
                        )
                elif not values_are_valid:
                    reason = "Moving-average warm-up is incomplete."

                signals.append(
                    TradingSignal(
                        symbol=str(symbol),
                        timestamp=row.timestamp.to_pydatetime(),
                        action=action,
                        confidence=1.0 if action != "HOLD" else 0.0,
                        reason=reason,
                        strategy_id=self.strategy_id,
                    )
                )
                previous_fast = current_fast if pd.notna(current_fast) else None
                previous_slow = current_slow if pd.notna(current_slow) else None
        return signals
