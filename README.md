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

`GET /api/backtests/run` reports the moving-average strategy beside a cost-adjusted Buy & Hold baseline over the same window. Results include turnover and turnover ratio, monthly returns, trade outcome/holding-period distributions, and equity/drawdown points. ML strategy comparison will be added when an ML strategy is connected to the backtest engine.

Run chronological walk-forward evaluation with `GET /api/backtests/walk-forward`. The endpoint reports separate training, validation, and test ranges and per-test-fold metrics. Its current baseline uses the same moving-average rule in each fold; the reusable `run_walk_forward` function accepts a strategy builder that can fit from the training and validation frames. Each test frame is passed to the backtest engine only after the strategy is built.

The baseline `POST /api/ml/train` endpoint supports Logistic Regression (default) and Random Forest via `model_type`; both use chronological splits (60% train, 20% validation, remaining rows test by default). Logistic Regression scaling is fit only on the training window. Its `metrics` field reports held-out test performance, and `validation_metrics` is reported separately. The response includes a dataset hash and model-version identifier. The trained pipeline and metadata are persisted in PostgreSQL by the `registered_models` migration. Training labels are supplied by the caller and must represent the intended future-period target; the endpoint does not construct targets from raw prices. Use `GET /api/models` to list registry entries and `POST /api/models/{model_version}/predict` with one feature value per registered feature to run an inference. Promote a selected version with `POST /api/models/{model_version}/promote`, inspect it with `GET /api/models/active`, and call `POST /api/models/predict` for default inference. Promotion only changes which registered model receives default predictions; it does not enable trading. Model artifacts are Python pickle data generated by this service; only trusted database artifacts should be loaded.

## Strategy decisions and paper orders

After ingesting OHLCV data, run the latest moving-average signal through risk checks with `POST /api/strategies/run` using `{"symbol":"DEMO","stop_loss_fraction":0.02}`. The API records the signal, risk result, and any staged paper order in PostgreSQL (`strategy_decisions` migration). A BUY is rejected while `ENABLE_TRADING=false`; an approved signal creates an unfilled paper order. Review decisions with `GET /api/strategies/decisions`. Filling remains a separate explicit call to `POST /api/paper-trading/orders/{id}/fill`; this strategy endpoint never fills orders automatically. Re-running the same strategy on the same symbol and bar is idempotent and returns the existing decision.

## Risk controls

New exposure is disabled by default with `ENABLE_TRADING=false`. Configure risk limits with `RISK_PER_TRADE`, `MAX_POSITION_FRACTION`, `MAX_PORTFOLIO_EXPOSURE_FRACTION`, `MAX_OPEN_POSITIONS`, `MAX_DAILY_LOSS_FRACTION`, `MAX_DRAWDOWN_FRACTION`, and `SYMBOL_COOLDOWN_SECONDS`; fractions must be greater than zero and at most one. Before a buy, the risk manager requires a stop price and caps size by stop-distance risk, available cash, per-position notional, total exposure, daily loss, drawdown, open positions, and the symbol cooldown. A sell can only reduce an existing long position, even while the kill switch is off:

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

The paper-order API uses the configured risk manager before accepting a new order. New buys require `ENABLE_TRADING=true`, an ingested market price or positive limit price, and a stop price; the requested quantity cannot exceed the risk-approved quantity. Sells are limited to reducing an existing paper position. Send an `Idempotency-Key` header to make order submission safe to retry: matching retries return the original order, while reusing a key with different order details returns HTTP 409. The key is stored with the order and protected by a database uniqueness constraint. The default kill switch is off. Paper orders, fills, and account state are stored in PostgreSQL and restored on restart. `POST /api/paper-trading/orders/{id}/fill` applies a simulated fill at the supplied reference price, including configured slippage and fees.

## Safety and scope

The broker mode is fixed to paper and live trading is disabled. The paper-order endpoint can submit unfilled paper orders after risk checks; it does not connect to an external broker. Backtests and paper-trading results are research outputs, not guarantees of future performance.

Set `API_AUTH_ENABLED=true` and provide an `API_KEY` of at least 32 characters to protect paper order operations, strategy execution and decision history, market-data ingestion, and model training/promotion with the `X-API-Key` request header. Production (`APP_ENV=production`) refuses to start without API auth enabled and a valid key. Development defaults to auth disabled for local setup. Configure browser origins as a comma-separated `CORS_ALLOWED_ORIGINS`; credentials are not allowed by CORS.

All `/api` requests use Redis-backed fixed-window rate limits configured by `RATE_LIMIT_REQUESTS` and `RATE_LIMIT_WINDOW_SECONDS` (120 requests per 60 seconds by default), counted by client address and, when sent, API key. Responses include rate-limit headers. Exceeding the limit returns HTTP 429 with `Retry-After`; if Redis is unavailable, API requests return HTTP 503. `/health` endpoints and test mode bypass rate limiting.

API write requests under `/api` create audit records with a generated request ID, actor category, route, method, response status, and UTC time. Request bodies, API keys, and other credentials are excluded. Browse recent records with `GET /api/audit-logs` (API key required when auth is enabled); records are stored in PostgreSQL by the `audit_logs` migration.
