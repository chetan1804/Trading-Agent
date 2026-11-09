# AI Automated Trading Platform

A modular research and paper-trading platform focused on Indian markets. Monetary values are denominated in Indian rupees (INR), and dashboard timestamps use India Standard Time. Development starts in paper mode; live trading is not implemented.

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

Run the read-only React operations dashboard in a second terminal:

```sh
cd frontend
npm install
npm run dev
```

It opens at <http://localhost:5173> and reads dashboard and monitoring snapshots from `http://localhost:8001` by default. Set `VITE_API_URL` to the API origin when the backend is hosted elsewhere. The dashboard displays currency in INR and times in IST, refreshes every 30 seconds, and shows portfolio, individual recent paper executions with fill quantity, price, fees and execution time, pre-trade risk limits, model monitoring, and alert snapshots; performance figures appear when supplied by a completed performance report. It does not submit or fill orders.

The **AI Research** section accepts a symbol, optional market snapshot, headlines, and document excerpts, then calls `POST /api/ai/research`. The current assistant creates a deterministic local summary from the supplied inputs; it does not fetch external data or call an LLM. Prices in the brief are labeled INR. The result is informational and cannot place orders.

`POST /api/ai/rag` accepts a query and a list of trusted document excerpts. Its lexical retrieval response includes source IDs (`document-1`, etc.), excerpt text, and relevance scores; answer text cites the IDs used. If no supplied excerpt matches query terms, it returns `no_relevant_sources` without presenting an unrelated excerpt as an answer. This is lightweight keyword retrieval, not an embedding model or an LLM, so review the cited source text directly.

The dashboard's **Run research agent** action calls `POST /api/agents/run` with the same supplied market snapshot, headlines, and document excerpts plus a research question. It displays the review plan, sentiment, cited excerpts, and missing-input/freshness warnings. This deterministic workflow does not fetch data, call an LLM, or place/approve orders.

Start PostgreSQL and Redis before running the API. The complete stack, including the API, PostgreSQL, Redis, and production-built dashboard, starts with `docker compose up --build`. The dashboard is available at <http://localhost:5173> and the API at <http://localhost:8001>. Set `VITE_API_URL` to the browser-reachable API origin when deploying elsewhere; it is embedded into the frontend at image build time. Set `FRONTEND_PORT` and `API_PORT` to change the local published ports. Compose uses local-only development credentials by default; override them with environment variables for non-local use. For a separately started API, apply schema changes with `make migrate` before `make run`.

## Checks

```sh
make test
make lint
```

`GET /health` checks API liveness. `GET /health/ready` checks PostgreSQL and Redis and returns 503 when either dependency is unavailable.

## Deployment

The backend and dashboard use separate containers. The backend image is built from the repository root, runs as the configured Uvicorn service, and has no live broker adapter. The dashboard is built as static assets and served by Nginx with SPA fallback and a container health endpoint. Compose waits for PostgreSQL/Redis and backend readiness before starting dependent services. CI runs tests and lint/format checks, then builds both container images; tagged releases publish the backend image to GitHub Container Registry.

For a hosted deployment, provide a managed PostgreSQL database and Redis service, set `APP_ENV=production`, enable API authentication with a unique `API_KEY` of at least 32 characters, and configure `CORS_ALLOWED_ORIGINS` for the dashboard origin. Set `VITE_API_URL` to the public HTTPS API origin before building the frontend image. Keep `ENABLE_TRADING=false`; the application has no live broker integration. Never use Compose's local fallback database credentials on a public host.

## Market data

Generate a reproducible synthetic OHLCV CSV with `uv run python scripts/generate_synthetic_data.py`. The default sample symbol is `RELIANCE.NS` (NSE); use `.NS` for NSE listings and `.BO` for BSE listings when supplying symbols. Synthetic prices are illustrative and are not actual Indian market data. CSV data uses `timestamp,symbol,open,high,low,close,volume`; run it through `trading.data.validation.validate_ohlcv` before research. Validation reports problems and normalizes timestamps/order, but does not drop rows or repair prices.

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

Backtest with next-bar-open fills, the illustrative default cost model, and optional protective exits:

```python
from trading.backtesting.engine import BacktestEngine
from trading.backtesting.metrics import calculate_performance_metrics
from trading.backtesting.costs import TransactionCosts
from trading.backtesting.engine import BacktestConfig

result = BacktestEngine().run(features, MovingAverageCrossoverStrategy())
metrics = calculate_performance_metrics(result.equity_curve, result.trades)
# Replace the illustrative default rates with your documented assumption.
custom_engine = BacktestEngine(BacktestConfig(costs=TransactionCosts(commission_rate=0.0005)))
# Optional: set `stop_loss_fraction=0.02` and/or `take_profit_fraction=0.05`
# on BacktestConfig to enable protective exits relative to the entry fill.
```

Default costs are placeholders (10 bps commission, 5 bps slippage, 2 bps spread); set `BacktestConfig(costs=TransactionCosts(...))` to match a documented market/broker assumption. Stop-loss and take-profit fractions are disabled by default. Stop-market exits use the stop level or a worse opening gap, then apply adverse slippage and spread. Take-profit limit exits use the target or a better opening price and apply commission. If a bar touches both levels, the simulator assumes the stop occurred first. The engine is single-symbol and long-only. Open final positions are marked to market, not forcibly liquidated.

`GET /api/backtests/run` reports the moving-average strategy beside a cost-adjusted Buy & Hold baseline over the same window. Results include turnover and turnover ratio, monthly returns, trade outcome/holding-period distributions, and equity/drawdown points. Optional `stop_loss_fraction` and `take_profit_fraction` query parameters enable protective exits.

Run chronological walk-forward evaluation with `GET /api/backtests/walk-forward`. The endpoint reports separate training, validation, and test ranges and per-test-fold metrics. It supports the moving-average baseline and `strategy_id=ml_probability` with Logistic Regression or Random Forest (`model_type`) and configurable buy/sell probability thresholds. Every fold compares the selected strategy with Moving Average and Buy & Hold on the same held-out test bars and transaction cost assumptions. The ML path constructs the target as next-bar close direction, fits only on the training window (the final training label becomes observable by the first validation close), then evaluates on the later test window. Rows with unavailable warm-up features are excluded from fitting. This is a baseline comparison, not a guarantee of future performance.

Example ML walk-forward request:

```sh
curl 'http://localhost:8001/api/backtests/walk-forward?symbol=RELIANCE.NS&limit=1000&training_window=252&validation_window=63&test_window=63&step_size=63&strategy_id=ml_probability&model_type=logistic_regression&buy_threshold=0.65&sell_threshold=0.35'
```

The baseline `POST /api/ml/train` endpoint supports Logistic Regression (default) and Random Forest via `model_type`; both use chronological splits (60% train, 20% validation, remaining rows test by default). Logistic Regression scaling is fit only on the training window. Its `metrics` field reports held-out test performance, and `validation_metrics` is reported separately. The response includes a dataset hash and model-version identifier. The trained pipeline and metadata are persisted in PostgreSQL by the `registered_models` migration. Training labels are supplied by the caller and must represent the intended future-period target; the endpoint does not construct targets from raw prices. Use `GET /api/models` to list registry entries and `POST /api/models/{model_version}/predict` with one feature value per registered feature to run an inference. Promote a selected version with `POST /api/models/{model_version}/promote`, inspect it with `GET /api/models/active`, and call `POST /api/models/predict` for default inference. Promotion only changes which registered model receives default predictions; it does not enable trading. Model artifacts are Python pickle data generated by this service; only trusted database artifacts should be loaded.

The `MLProbabilityStrategy` adapter converts a trusted trained artifact's positive-class probabilities into BUY/SELL/HOLD signals using configurable thresholds. Use it with `BacktestEngine` on a strictly out-of-sample feature frame; the engine executes close-time signals at the next bar open. The model must not have been trained on any evaluated rows, and labels should describe the future horizon represented by the strategy. The API backtest comparison currently remains moving-average versus Buy & Hold; it does not yet load registered models for backtesting.

Each prediction response now includes a `prediction_id`; prediction inputs and outputs are stored for monitoring. After the target period has elapsed, record its binary outcome with `POST /api/models/predictions/{prediction_id}/outcome` and `{"actual_label": 1}` (requires API auth when enabled). Identical retries are safe; a different label cannot overwrite an outcome. Model monitoring compares observed feature means with the training-window baseline and computes accuracy, precision, and recall from labeled observations. It reports `collecting` until at least 20 observations exist, flags feature drift after that threshold, and withholds quality alerts until at least 20 outcomes are labeled. Apply the `model_observations` migration before using these endpoints.

## Strategy decisions and paper orders

After ingesting Indian-market OHLCV data, run the latest moving-average signal through risk checks with `POST /api/strategies/run` using `{"symbol":"RELIANCE.NS","stop_loss_fraction":0.02}`. The API records the signal, risk result, and any staged paper order in PostgreSQL (`strategy_decisions` migration). A BUY is rejected while `ENABLE_TRADING=false`; an approved signal creates an unfilled paper order. Review decisions with `GET /api/strategies/decisions`. Filling remains a separate explicit call to `POST /api/paper-trading/orders/{id}/fill`; this strategy endpoint never fills orders automatically. Re-running the same strategy on the same symbol and bar is idempotent and returns the existing decision.

## Risk controls

New exposure is disabled by default with `ENABLE_TRADING=false`. Configure risk limits with `RISK_PER_TRADE`, `MAX_POSITION_FRACTION`, `MAX_PORTFOLIO_EXPOSURE_FRACTION`, `MAX_OPEN_POSITIONS`, `MAX_DAILY_LOSS_FRACTION`, `MAX_DRAWDOWN_FRACTION`, and `SYMBOL_COOLDOWN_SECONDS`; fractions must be greater than zero and at most one. Before a buy, the risk manager requires a stop price and caps size by stop-distance risk, available cash, per-position notional, total exposure, daily loss, drawdown, open positions, and the symbol cooldown. A sell can only reduce an existing long position, even while the kill switch is off:

The dashboard risk summary reports the kill-switch state and current exposure, drawdown, open positions, and daily realized P&amp;L against their configured pre-trade limits. Daily loss currently tracks realized paper-broker P&amp;L; it is distinct from the portfolio's net realized-plus-unrealized P&amp;L.

The dashboard **Backtesting** section offers a single-window run or chronological walk-forward evaluation. Single-window runs support moving-average crossover and buy-and-hold with configurable date range, costs, and optional stop-loss/take-profit fractions. Walk-forward runs support moving-average crossover or ML probability signals with configurable training, validation, test, and step windows; ML runs also expose classifier and buy/sell thresholds. Both modes can apply stop-loss and take-profit exits. Each held-out fold shows selected strategy returns beside Moving Average and Buy & Hold returns on the same test bars. Both modes prefer ingested bars and label fallback synthetic data; simulations remain single-symbol and long-only.

```python
from datetime import UTC, datetime

from app.config import get_settings
from trading.risk.manager import AccountRiskState, RiskManager, TradeProposal

risk = RiskManager(enabled=get_settings().enable_trading)
proposal = TradeProposal(
    symbol="RELIANCE.NS",
    side="BUY",
    entry_price=100,
    stop_loss_price=95,
    timestamp=datetime.now(UTC),
)
account_state = AccountRiskState(equity=100_000, available_cash=100_000)
decision = risk.evaluate(proposal, account_state)
```

The paper-order API uses the configured risk manager before accepting a new order. New buys require `ENABLE_TRADING=true`, an ingested market price or positive limit price, and a stop price; the requested quantity cannot exceed the risk-approved quantity. Sells are limited to reducing an existing paper position. Send an `Idempotency-Key` header to make order submission safe to retry: matching retries return the original order, while reusing a key with different order details returns HTTP 409. The key is stored with the order and protected by a database uniqueness constraint. The default kill switch is off. Paper orders, individual executions, and account state are stored in PostgreSQL and restored on restart. `POST /api/paper-trading/orders/{id}/fill` applies a simulated fill at the supplied reference price, including configured slippage and fees. Send an `Idempotency-Key` header on fill requests to safely retry a partial fill; a reused key with different request details returns HTTP 409. Browse the in-memory recent ledger with `GET /api/paper-trading/executions` (API key required when auth is enabled).

To evaluate already-submitted paper `STOP` and `LIMIT` orders against a candle, send its OHLC values to `POST /api/paper-trading/market-update`. The endpoint only matches active orders for that symbol; it never creates an order. Bar timestamps must be newer than the previous market update and paper fill for that symbol; duplicate or out-of-order updates return HTTP 409, and the last processed timestamp survives restarts. Stop orders fill at the trigger or a worse opening gap. Limit orders fill at the limit or a better opening price and are not filled past their limit after slippage. Fees apply and the close updates portfolio marks. To stage a stop-loss and take-profit pair, submit both sell orders with the same `oco_group`, symbol, and quantity. When either order fills, its active siblings are cancelled; if one candle touches both, STOP orders are checked first. Triggered and cancelled orders plus the portfolio snapshot are persisted together. The endpoint requires an API key when authentication is enabled.

## Safety and scope

The broker mode is fixed to paper and live trading is disabled. The paper-order endpoint can submit unfilled paper orders after risk checks; it does not connect to an external broker. Backtests and paper-trading results are research outputs, not guarantees of future performance.

Set `API_AUTH_ENABLED=true` and provide an `API_KEY` of at least 32 characters to protect paper order operations, strategy execution and decision history, market-data ingestion, and model training/promotion with the `X-API-Key` request header. Production (`APP_ENV=production`) refuses to start without API auth enabled and a valid key. Development defaults to auth disabled for local setup. Configure browser origins as a comma-separated `CORS_ALLOWED_ORIGINS`; credentials are not allowed by CORS.

All `/api` requests use Redis-backed fixed-window rate limits configured by `RATE_LIMIT_REQUESTS` and `RATE_LIMIT_WINDOW_SECONDS` (120 requests per 60 seconds by default), counted by client address and, when sent, API key. Responses include rate-limit headers. Exceeding the limit returns HTTP 429 with `Retry-After`; if Redis is unavailable, API requests return HTTP 503. `/health` endpoints and test mode bypass rate limiting.

API write requests under `/api` create audit records with a generated request ID, actor category, route, method, response status, and UTC time. Request bodies, API keys, and other credentials are excluded. Browse recent records with `GET /api/audit-logs` (API key required when auth is enabled); records are stored in PostgreSQL by the `audit_logs` migration.
