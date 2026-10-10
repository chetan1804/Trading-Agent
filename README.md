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

For PostgreSQL and Redis, start the complete local stack with `docker compose up --build`. Compose uses local-only development credentials by default; override them with environment variables for non-local use.

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

## Safety and scope

The broker mode is fixed to paper and live trading is disabled. This foundation does not submit orders. Backtests and paper-trading results are research outputs, not guarantees of future performance.
