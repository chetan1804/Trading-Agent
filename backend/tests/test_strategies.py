from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest
from trading.strategies.moving_average import MovingAverageCrossoverStrategy


def _feature_rows(
    symbol: str,
    fast_values: list[float],
    slow_values: list[float],
    start_hour: int = 0,
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": [
                datetime(2024, 1, 1, tzinfo=UTC) + timedelta(hours=start_hour + index)
                for index in range(len(fast_values))
            ],
            "symbol": symbol,
            "sma_2": fast_values,
            "sma_3": slow_values,
        }
    )


def test_strategy_emits_buy_and_sell_only_on_crossovers() -> None:
    data = _feature_rows("DEMO", [0.5, 0.8, 2, 2, 1], [1, 1, 1, 2, 2])
    strategy = MovingAverageCrossoverStrategy(fast_window=2, slow_window=3)

    signals = strategy.generate_signals(data)

    assert [signal.action for signal in signals] == ["HOLD", "HOLD", "BUY", "HOLD", "SELL"]
    assert signals[2].confidence == 1.0
    assert "next bar" in signals[2].reason
    assert all(signal.strategy_id == "moving_average_crossover_2_3" for signal in signals)


def test_strategy_handles_warmup_and_unsorted_input() -> None:
    data = _feature_rows("DEMO", [float("nan"), 1, 2], [float("nan"), 2, 1])
    data = data.iloc[::-1]
    strategy = MovingAverageCrossoverStrategy(fast_window=2, slow_window=3)

    signals = strategy.generate_signals(data)

    assert [signal.action for signal in signals] == ["HOLD", "HOLD", "BUY"]
    assert signals[0].reason == "Moving-average warm-up is incomplete."
    timestamps = [signal.timestamp for signal in signals]
    assert timestamps == sorted(timestamps)


def test_strategy_keeps_symbol_crossings_independent() -> None:
    first = _feature_rows("AAA", [1, 2], [2, 1])
    second = _feature_rows("BBB", [2, 1], [1, 2])
    data = pd.concat([first, second], ignore_index=True)
    strategy = MovingAverageCrossoverStrategy(fast_window=2, slow_window=3)

    signals = strategy.generate_signals(data)
    actions_by_symbol = {
        symbol: [signal.action for signal in signals if signal.symbol == symbol]
        for symbol in ("AAA", "BBB")
    }

    assert actions_by_symbol == {"AAA": ["HOLD", "BUY"], "BBB": ["HOLD", "SELL"]}


def test_strategy_validates_windows_and_required_columns() -> None:
    with pytest.raises(ValueError, match="smaller"):
        MovingAverageCrossoverStrategy(fast_window=5, slow_window=5)
    with pytest.raises(ValueError, match="Missing strategy input columns"):
        MovingAverageCrossoverStrategy(fast_window=2, slow_window=3).generate_signals(
            pd.DataFrame({"timestamp": [], "symbol": []})
        )
