# AI Automated Trading Platform

A modular trading research platform. Development starts in paper mode; live trading is not implemented.

## Requirements

- Python 3.12 or newer and [uv](https://docs.astral.sh/uv/)
- Docker Desktop for the full local stack

## Local setup

```sh
cp .env.example .env
uv sync --extra dev
make run
```

The API listens at <http://localhost:8001>. Interactive API documentation is at <http://localhost:8001/docs>.

Start PostgreSQL and Redis before running the API. The complete stack, including automatic database migrations, starts with `docker compose up --build`. Compose uses local-only development credentials by default; override them with environment variables for non-local use. For a separately started API, apply schema changes with `make migrate` before `make run`.

## Checks

```sh
make test
make lint
```

`GET /health` checks API liveness. `GET /health/ready` checks PostgreSQL and Redis and returns 503 when either dependency is unavailable.

## Market data

Generate a reproducible synthetic OHLCV CSV with `uv run python scripts/generate_synthetic_data.py`. CSV data uses `timestamp,symbol,open,high,low,close,volume`; run it through `trading.data.validation.validate_ohlcv` before research. Validation reports problems and normalizes timestamps/order, but does not drop rows or repair prices.

Generate causal, per-symbol features with:

```python
from trading.data.synthetic import generate_synthetic_ohlcv
from trading.features.feature_pipeline import engineer_features

bars = generate_synthetic_ohlcv()
features = engineer_features(bars)
```

Rolling features use current and prior observations only. Warm-up periods remain missing; they are not backfilled.

## Baseline strategy

Generate structured moving-average crossover signals from engineered features:

```python
from trading.data.synthetic import generate_synthetic_ohlcv
from trading.features.feature_pipeline import engineer_features
from trading.strategies.moving_average import MovingAverageCrossoverStrategy

features = engineer_features(generate_synthetic_ohlcv())
signals = MovingAverageCrossoverStrategy().generate_signals(features)
```

The default strategy uses SMA 20 and SMA 50. It emits BUY or SELL only on a crossover and HOLD otherwise. Signals are observations at bar close, not orders; any execution must be evaluated no earlier than the next bar and pass separate risk controls.

Backtest with next-bar-open fills and the illustrative default cost model:

```python
from trading.backtesting.engine import BacktestEngine
from trading.backtesting.metrics import calculate_performance_metrics
from trading.backtesting.costs import TransactionCosts
from trading.backtesting.engine import BacktestConfig

result = BacktestEngine().run(features, MovingAverageCrossoverStrategy())
metrics = calculate_performance_metrics(result.equity_curve, result.trades)
# Replace the illustrative default rates with your documented assumption.
custom_engine = BacktestEngine(BacktestConfig(costs=TransactionCosts(commission_rate=0.0005)))
```

Default costs are placeholders (10 bps commission, 5 bps slippage, 2 bps spread); set `BacktestConfig(costs=TransactionCosts(...))` to match a documented market/broker assumption. The initial engine is single-symbol and long-only. Open final positions are marked to market, not forcibly liquidated.

## Risk controls

New exposure is disabled by default with `ENABLE_TRADING=false`. Before a buy, the risk manager requires a stop price and caps size by stop-distance risk, available cash, per-position notional, total exposure, daily loss, drawdown, open positions, and the symbol cooldown. A sell can only reduce an existing long position, even while the kill switch is off:

```python
from datetime import UTC, datetime

from app.config import get_settings
from trading.risk.manager import AccountRiskState, RiskManager, TradeProposal

risk = RiskManager(enabled=get_settings().enable_trading)
proposal = TradeProposal(
    symbol="DEMO",
    side="BUY",
    entry_price=100,
    stop_loss_price=95,
    timestamp=datetime.now(UTC),
)
account_state = AccountRiskState(equity=100_000, available_cash=100_000)
decision = risk.evaluate(proposal, account_state)
```

The paper-order API uses the configured risk manager before accepting a new order. New buys require `ENABLE_TRADING=true`, an ingested market price or positive limit price, and a stop price; the requested quantity cannot exceed the risk-approved quantity. Sells are limited to reducing an existing paper position. The default kill switch is off. Paper order submissions and cancellations are stored in PostgreSQL and restored on restart; paper balances and positions are still in memory.

## Safety and scope

The broker mode is fixed to paper and live trading is disabled. The paper-order endpoint can submit unfilled paper orders after risk checks; it does not connect to an external broker. Backtests and paper-trading results are research outputs, not guarantees of future performance.
