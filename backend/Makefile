.PHONY: install test lint format typecheck check run ci

install:
	uv sync

test:
	uv run pytest -v

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run mypy app

check: lint typecheck test

run:
	uv run uvicorn app.main:app --reload --port 8000

ci: lint format typecheck test
