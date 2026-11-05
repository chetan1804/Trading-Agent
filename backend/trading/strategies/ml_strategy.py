from dataclasses import dataclass
from datetime import UTC

import pandas as pd

from trading.ml.trainer import SignalModelTrainer
from trading.strategies.base import SignalAction, TradingSignal


@dataclass(frozen=True)
class MLProbabilityStrategy:
    """Convert positive-class probabilities into timestamped research signals.

    The supplied artifact must have been trained without using the rows being
    evaluated. Signals are observed at bar close; BacktestEngine executes them
    at the following bar's open.
    """

    artifact: bytes
    feature_names: tuple[str, ...]
    buy_threshold: float = 0.65
    sell_threshold: float = 0.35
    model_version: str = "unversioned"

    def __post_init__(self) -> None:
        if not self.artifact:
            raise ValueError("model artifact must not be empty")
        if not self.feature_names or len(set(self.feature_names)) != len(self.feature_names):
            raise ValueError("feature_names must be non-empty and unique")
        if not 0 <= self.sell_threshold < self.buy_threshold <= 1:
            raise ValueError("thresholds must satisfy 0 <= sell < buy <= 1")

    @property
    def strategy_id(self) -> str:
        return f"ml_probability_{self.model_version}"

    def generate_signals(self, market_data: pd.DataFrame) -> list[TradingSignal]:
        required = {"timestamp", "symbol", *self.feature_names}
        missing = sorted(required.difference(market_data.columns))
        if missing:
            raise ValueError(f"Missing strategy input columns: {', '.join(missing)}")

        data = market_data.copy()
        data["timestamp"] = pd.to_datetime(data["timestamp"], utc=True, errors="coerce")
        if data["timestamp"].isna().any():
            raise ValueError("Strategy input contains invalid timestamps")
        data = data.sort_values(["symbol", "timestamp"], kind="stable")

        signals: list[TradingSignal] = []
        for _, row in data.iterrows():
            values = {name: float(row[name]) for name in self.feature_names}
            probability = SignalModelTrainer.predict_probability(
                self.artifact,
                feature_names=list(self.feature_names),
                features=values,
            )
            action: SignalAction = "HOLD"
            reason = f"Positive-return probability {probability:.3f} is between thresholds."
            confidence = probability
            if probability >= self.buy_threshold:
                action = "BUY"
                reason = (
                    f"Positive-return probability {probability:.3f} meets buy threshold "
                    f"{self.buy_threshold:.3f}; evaluate execution no earlier than the next bar."
                )
            elif probability <= self.sell_threshold:
                action = "SELL"
                confidence = 1.0 - probability
                reason = (
                    f"Positive-return probability {probability:.3f} meets sell threshold "
                    f"{self.sell_threshold:.3f}; evaluate execution no earlier than the next bar."
                )
            signals.append(
                TradingSignal(
                    symbol=str(row["symbol"]),
                    timestamp=row["timestamp"].to_pydatetime().astimezone(UTC),
                    action=action,
                    confidence=float(confidence),
                    reason=reason,
                    strategy_id=self.strategy_id,
                )
            )
        return signals
