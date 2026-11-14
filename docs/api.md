# API reference

The API is served by FastAPI. For a local run, the base URL is `http://localhost:8001`; the interactive OpenAPI page is at `/docs` and the schema is at `/openapi.json`.

All routes below are relative to the base URL. Paths beginning with `/api` are subject to Redis-backed rate limits. In production, configure `API_AUTH_ENABLED=true` and a unique `API_KEY` of at least 32 characters. Routes marked **Key when enabled** require `X-API-Key` when API authentication is enabled. Routes marked **No route key** do not declare that dependency.

## Health

| Method | Path | Description | Access |
| --- | --- | --- | --- |
| `GET` | `/health` | Liveness check; returns `{"status":"ok"}`. | Public |
| `GET` | `/health/ready` | Checks PostgreSQL, Redis, market-data access (stored bars with synthetic fallback), the paper broker adapter, and model-service configuration; returns 503 if any check is unavailable. | Public |

Health routes are outside the `/api` rate limiter.

## Market data and features

| Method | Path | Description | Access |
| --- | --- | --- | --- |
| `GET` | `/api/market-data/quote` | Latest cached or synthetic quote. Query: `symbol` (default `RELIANCE.NS`). | No route key |
| `GET` | `/api/market-data/history` | Recent cached or synthetic OHLCV bars. Query: `symbol`, `limit` (1–500, default 20). | No route key |
| `GET` | `/api/market-data/news` | Deterministic sample headlines. Query: `symbol`, `limit` (1–10, default 5). | No route key |
| `GET` | `/api/market-data/validate` | Basic checks on cached or synthetic bars. Query: `symbol`, `limit` (1–500, default 20). | No route key |
| `GET` | `/api/market-data/stored` | Cached bars currently available to this API process. Query: `symbol`, `limit` (1–500, default 50). | No route key |
| `POST` | `/api/market-data/ingest` | Validate, persist, and cache supplied OHLCV bars. | Key when enabled |
| `GET` | `/api/features/engineer` | Latest engineered feature rows. Query: `symbol`, `limit` (1–200, default 20). | No route key |
| `POST` | `/api/news/ingest` | Normalize supplied headlines, deduplicate them, score lexical sentiment, and persist the results. Accepts 1–500 articles. | Key when enabled |
| `GET` | `/api/news` | Recent persisted headlines and sentiment. Query: required `symbol`, `limit` (1–200, default 20). | No route key |

Market-data bars use timestamps and `open`, `high`, `low`, `close`, and `volume`. Ingestion normalizes naive timestamps as UTC, validates OHLC constraints, and upserts by symbol and timestamp. The `stored` endpoint returns the process cache; PostgreSQL is the durable store.

News ingestion only processes caller-supplied articles; it does not connect to external feeds. Duplicate detection uses normalized symbol, source, and headline. Sentiment uses the local keyword analyzer; confidence is the absolute sentiment score, not a calibrated probability. Apply migration `20261114_0015` before using the news endpoints.

Example ingestion request:

```sh
curl -X POST 'http://localhost:8001/api/market-data/ingest' \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: YOUR_API_KEY' \
  -d '{
    "symbol": "RELIANCE.NS",
    "bars": [{
      "timestamp": "2026-11-12T10:00:00Z",
      "open": 1450.0,
      "high": 1462.0,
      "low": 1445.0,
      "close": 1458.0,
      "volume": 125000
    }]
  }'
```

Omit `X-API-Key` only when API authentication is disabled. Synthetic fallback data is illustrative, not actual market data.

## Strategies, backtests, and risk

| Method | Path | Description | Access |
| --- | --- | --- | --- |
| `GET` | `/api/strategies/generate` | Generate moving-average signals from cached or synthetic bars. Query: `symbol`, `limit` (1–200, default 20). | No route key |
| `POST` | `/api/strategies/run` | Evaluate latest ingested bar, risk-check a signal, and record a decision or stage an unfilled paper order. | Key when enabled |
| `GET` | `/api/strategies/decisions` | Recent strategy decisions. Query: `limit` (1–200, default 50). | Key when enabled |
| `GET` | `/api/backtests/run` | Single-window moving-average or Buy & Hold backtest and comparison. | No route key |
| `GET` | `/api/backtests/walk-forward` | Chronological fold evaluation; supports moving-average and ML probability strategies. | No route key |
| `POST` | `/api/risk/evaluate` | Evaluate a supplied proposal and account state against configured risk limits. | No route key |

Backtest parameters:

- `/api/backtests/run`: `symbol`, `strategy_id`, `limit`, `initial_cash`, `commission_rate`, `slippage_bps`, `spread_bps`, optional `start_date`, `end_date`, `stop_loss_fraction`, and `take_profit_fraction`.
- `/api/backtests/walk-forward`: `symbol`, `limit`, `training_window`, `validation_window`, `test_window`, `step_size`, `initial_cash`, `strategy_id`, `model_type`, `buy_threshold`, `sell_threshold`, and optional stop/take-profit fractions.

The detailed output includes metrics, trades, equity points, and benchmark comparisons. Historical results do not predict future returns. For example:

```sh
curl -G 'http://localhost:8001/api/backtests/walk-forward' \
  --data-urlencode 'symbol=RELIANCE.NS' \
  --data-urlencode 'limit=1000' \
  --data-urlencode 'training_window=252' \
  --data-urlencode 'validation_window=63' \
  --data-urlencode 'test_window=63' \
  --data-urlencode 'step_size=63' \
  --data-urlencode 'strategy_id=ml_probability' \
  --data-urlencode 'model_type=logistic_regression'
```

`POST /api/strategies/run` requires ingested bars. A typical body is `{"symbol":"RELIANCE.NS","stop_loss_fraction":0.02}`. An approved BUY still requires `ENABLE_TRADING=true`; this endpoint stages an unfilled paper order and does not fill it.

## Models and monitoring

| Method | Path | Description | Access |
| --- | --- | --- | --- |
| `POST` | `/api/ml/train` | Chronologically train and register Logistic Regression or Random Forest. | Key when enabled |
| `GET` | `/api/models` | List registered model metadata. | No route key |
| `GET` | `/api/models/active` | Get the promoted model metadata. | No route key |
| `POST` | `/api/models/{model_version}/predict` | Predict from a registered model and record a prediction observation. | No route key |
| `POST` | `/api/models/predict` | Predict using the currently promoted model and record an observation. | No route key |
| `POST` | `/api/models/predictions/{prediction_id}/outcome` | Record the later binary outcome for a prediction. | Key when enabled |
| `POST` | `/api/models/{model_version}/promote` | Select a registered model for default inference. | Key when enabled |
| `GET` | `/api/monitoring/overview` | Model and paper-execution monitoring snapshot with alerts. | No route key |

Training body:

```json
{
  "features": {
    "return_1": [0.01, -0.02, 0.03, 0.01, -0.01, 0.02, -0.03, 0.01, 0.02, -0.01],
    "rsi_14": [48, 52, 55, 49, 47, 53, 44, 51, 56, 50]
  },
  "labels": [1, 0, 1, 0, 1, 0, 0, 1, 1, 0],
  "model_type": "logistic_regression",
  "train_fraction": 0.6,
  "validation_fraction": 0.2
}
```

Feature arrays must have equal lengths and labels must be binary. Labels are caller-provided: construct the intended future-period target without crossing chronological split boundaries. Predictions return a `prediction_id`; submit its eventual outcome only after the target horizon has elapsed. Model promotion affects default inference only and does not enable paper trading.

## Portfolio and paper trading

| Method | Path | Description | Access |
| --- | --- | --- | --- |
| `GET` | `/api/dashboard/overview` | Combined portfolio, performance, execution, and risk dashboard snapshot. | No route key |
| `GET` | `/api/portfolio/summary` | Current paper cash, positions, marks, and P&L. | No route key |
| `GET` | `/api/portfolio/snapshot` | Alias returning the current portfolio snapshot. | No route key |
| `GET` | `/api/performance/summary` | Marked account return, P&L, fills, and available historical metrics. | No route key |
| `POST` | `/api/paper-trading/orders` | Risk-check and stage an unfilled paper order. | Key when enabled |
| `POST` | `/api/paper-trading/orders/{order_id}/cancel` | Cancel an active paper order. | Key when enabled |
| `POST` | `/api/paper-trading/orders/{order_id}/fill` | Apply an explicit simulated fill with fees and slippage. | Key when enabled |
| `POST` | `/api/paper-trading/market-update` | Match existing STOP/LIMIT orders against an OHLC bar and update marks. | Key when enabled |
| `GET` | `/api/paper-trading/orders` | List paper orders. | Key when enabled |
| `GET` | `/api/paper-trading/executions` | Recent fill-level execution ledger. Query: `limit` (1–500, default 100). | Key when enabled |

For order creation, send `symbol`, `side` (`BUY`/`SELL`), `quantity`, `order_type` (`MARKET`/`LIMIT`/`STOP`), and the corresponding optional `limit_price`, `stop_price`, and `oco_group` values. `Idempotency-Key` can be sent on order creation and fill requests to make supported retries safe. New buys are blocked unless `ENABLE_TRADING=true` and risk checks approve them. Sells can only reduce an existing long position.

Example explicit fill request:

```sh
curl -X POST 'http://localhost:8001/api/paper-trading/orders/ORDER_ID/fill' \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: YOUR_API_KEY' \
  -H 'Idempotency-Key: fill-request-0001' \
  -d '{"price": 1458.0, "quantity": 2}'
```

Market updates match existing orders only; they do not create orders. Bar timestamps must be newer than the previous update and paper fill for that symbol. Duplicate or out-of-order bars return 409. When using OCO exits, STOP matching is checked before LIMIT matching if one bar touches both.

## AI research, audit, and deployment status

| Method | Path | Description | Access |
| --- | --- | --- | --- |
| `POST` | `/api/ai/research` | Deterministic summary of caller-supplied snapshot, headlines, and excerpts. | No route key |
| `POST` | `/api/ai/sentiment` | Rule-based sentiment summary of supplied headlines. | No route key |
| `POST` | `/api/ai/rag` | Lexical retrieval and answer with IDs for supplied document excerpts. | No route key |
| `POST` | `/api/agents/run` | Deterministic research workflow over caller-supplied inputs. | No route key |
| `GET` | `/api/audit-logs` | Recent write-request audit metadata. Query: `limit` (1–500, default 100). | Key when enabled |
| `GET` | `/api/broker/status` | Configured broker mode and live-trading status. | No route key |
| `GET` | `/api/deployment/status` | Runtime configuration and deployment readiness summary. | No route key |

AI and agent endpoints do not fetch external news, call an LLM, approve trades, or submit orders. Audit records contain request metadata, not request bodies, API keys, or other credentials.

## Common errors and operational notes

- `401`: missing or invalid `X-API-Key` on a protected route when API authentication is enabled.
- `409`: conflicting idempotency key, duplicate or stale market bar, or invalid order lifecycle transition.
- `422`: invalid request data or unsupported backtest/model parameters.
- `429`: API rate limit exceeded; the response includes `Retry-After`.
- `503`: a required dependency or storage service is unavailable.

Rate-limit settings are `RATE_LIMIT_REQUESTS` and `RATE_LIMIT_WINDOW_SECONDS`. Health endpoints and test mode bypass the API limiter. The API is paper-only; live broker execution is not implemented.
