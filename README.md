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

## Safety and scope

The broker mode is fixed to paper and live trading is disabled. This foundation does not submit orders. Backtests and paper-trading results are research outputs, not guarantees of future performance.
