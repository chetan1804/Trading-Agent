.PHONY: install test lint format run docker-up docker-down

install:
	uv sync --extra dev

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

run:
	uv run uvicorn app.main:app --app-dir backend --reload --port 8001

docker-up:
	docker compose up --build

docker-down:
	docker compose down