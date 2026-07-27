.PHONY: setup check format test smoke verify

setup:
	uv sync --group dev
	uv run pre-commit install

check:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff check --fix .
	uv run ruff format .

test:
	uv run pytest -q

smoke:
	uv run pytest -q tests/smoke

verify: check test
