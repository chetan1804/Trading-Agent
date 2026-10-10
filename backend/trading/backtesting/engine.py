import math
from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from trading.backtesting.costs import TransactionCosts
from trading.data.validation import validate_ohlcv
from trading.strategies.base import Strategy, TradingSignal


@dataclass(frozen=True)
class BacktestConfig:
    initial_cash: float = 100_000.0
    position_size_fraction: float = 1.0
    costs: TransactionCosts = TransactionCosts()

    def __post_init__(self) -> None:
        if self.initial_cash <= 0:
            raise ValueError("initial_cash must be positive")
        if not 0 < self.position_size_fraction <= 1:
            raise ValueError("position_size_fraction must be greater than 0 and at most 1")


@dataclass(frozen=True)
class BacktestTrade:
    symbol: str
    strategy_id: str
    entry_time: datetime
    exit_time: datetime
    quantity: float
    entry_price: float
    exit_price: float
    entry_commission: float
    exit_commission: float
    pnl: float
    return_fraction: float
    holding_bars: int


@dataclass(frozen=True)
class OpenPosition:
    symbol: str
    strategy_id: str
    entry_time: datetime
    quantity: float
    entry_price: float
    entry_commission: float
    entry_bar: int


@dataclass
class BacktestResult:
    initial_cash: float
    ending_cash: float
    ending_equity: float
    trades: pd.DataFrame
    equity_curve: pd.DataFrame
    open_position: OpenPosition | None
    turnover: float


class BacktestEngine:
    """Run a single-symbol, long-only strategy with next-observation open fills."""

    def __init__(self, config: BacktestConfig | None = None) -> None:
        self.config = config or BacktestConfig()

    def run(self, market_data: pd.DataFrame, strategy: Strategy) -> BacktestResult:
        report = validate_ohlcv(market_data, max_abs_close_return=None)
        if report.has_errors:
            codes = sorted({issue.code for issue in report.issues if issue.severity == "error"})
            raise ValueError(f"Cannot backtest invalid OHLCV data: {', '.join(codes)}")
        if report.data.empty:
            raise ValueError("market_data cannot be empty")
        symbols = report.data["symbol"].dropna().astype(str).unique()
        if len(symbols) != 1:
            raise ValueError("BacktestEngine currently supports exactly one symbol")
        if report.data["close"].le(0).any() or report.data["open"].le(0).any():
            raise ValueError("open and close prices must be positive")

        bars = report.data.sort_values("timestamp", kind="stable").reset_index(drop=True)
        signals = strategy.generate_signals(bars)
        signal_by_time = self._index_signals(signals, str(symbols[0]))

        cash = self.config.initial_cash
        position: OpenPosition | None = None
        pending_signal: TradingSignal | None = None
        closed_trades: list[BacktestTrade] = []
        equity_rows: list[dict[str, object]] = []
        turnover = 0.0

        for bar_index, bar in bars.iterrows():
            timestamp = pd.Timestamp(bar["timestamp"])
            if pending_signal is not None:
                if pending_signal.action == "BUY" and position is None:
                    fill_price = self.config.costs.fill_price(float(bar["open"]), "BUY")
                    budget = cash * self.config.position_size_fraction
                    quantity = max(
                        0.0,
                        (budget - self.config.costs.fixed_commission)
                        / (fill_price * (1 + self.config.costs.commission_rate)),
                    )
                    notional = quantity * fill_price
                    entry_commission = self.config.costs.commission(notional)
                    total_cost = notional + entry_commission
                    if total_cost > cash and quantity > 0:
                        quantity = math.nextafter(quantity * cash / total_cost, 0.0)
                        notional = quantity * fill_price
                        entry_commission = self.config.costs.commission(notional)
                        total_cost = notional + entry_commission
                    if quantity > 0 and total_cost <= cash:
                        cash -= notional + entry_commission
                        turnover += notional
                        position = OpenPosition(
                            symbol=str(bar["symbol"]),
                            strategy_id=pending_signal.strategy_id,
                            entry_time=timestamp.to_pydatetime(),
                            quantity=quantity,
                            entry_price=fill_price,
                            entry_commission=entry_commission,
                            entry_bar=bar_index,
                        )
                elif pending_signal.action == "SELL" and position is not None:
                    fill_price = self.config.costs.fill_price(float(bar["open"]), "SELL")
                    notional = position.quantity * fill_price
                    exit_commission = self.config.costs.commission(notional)
                    cash += notional - exit_commission
                    turnover += notional
                    pnl = (
                        (fill_price - position.entry_price) * position.quantity
                        - position.entry_commission
                        - exit_commission
                    )
                    entry_notional = position.entry_price * position.quantity
                    closed_trades.append(
                        BacktestTrade(
                            symbol=position.symbol,
                            strategy_id=position.strategy_id,
                            entry_time=position.entry_time,
                            exit_time=timestamp.to_pydatetime(),
                            quantity=position.quantity,
                            entry_price=position.entry_price,
                            exit_price=fill_price,
                            entry_commission=position.entry_commission,
                            exit_commission=exit_commission,
                            pnl=pnl,
                            return_fraction=pnl / (entry_notional + position.entry_commission),
                            holding_bars=bar_index - position.entry_bar,
                        )
                    )
                    position = None

            market_value = position.quantity * float(bar["close"]) if position else 0.0
            equity_rows.append(
                {
                    "timestamp": timestamp,
                    "cash": cash,
                    "market_value": market_value,
                    "equity": cash + market_value,
                    "exposure": market_value,
                }
            )
            pending_signal = signal_by_time.get(timestamp)

        equity_curve = pd.DataFrame(equity_rows)
        equity_curve["peak_equity"] = equity_curve["equity"].cummax()
        equity_curve["drawdown"] = equity_curve["equity"] / equity_curve["peak_equity"] - 1
        ending_equity = float(equity_curve["equity"].iloc[-1])
        trade_columns = [field for field in BacktestTrade.__dataclass_fields__]
        trades = pd.DataFrame(
            [trade.__dict__ for trade in closed_trades],
            columns=trade_columns,
        )
        return BacktestResult(
            initial_cash=self.config.initial_cash,
            ending_cash=cash,
            ending_equity=ending_equity,
            trades=trades,
            equity_curve=equity_curve,
            open_position=position,
            turnover=turnover,
        )

    @staticmethod
    def _index_signals(
        signals: list[TradingSignal],
        symbol: str,
    ) -> dict[pd.Timestamp, TradingSignal]:
        indexed: dict[pd.Timestamp, TradingSignal] = {}
        for signal in signals:
            if signal.symbol != symbol or signal.action == "HOLD":
                continue
            timestamp = pd.Timestamp(signal.timestamp)
            if timestamp.tzinfo is None:
                timestamp = timestamp.tz_localize("UTC")
            else:
                timestamp = timestamp.tz_convert("UTC")
            if timestamp in indexed:
                raise ValueError(f"Multiple actionable signals at {timestamp}")
            indexed[timestamp] = signal
        return indexed
