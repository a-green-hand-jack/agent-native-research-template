.PHONY: setup hooks check format test smoke research-validate research-run verify

setup:
	uv sync --group dev

hooks:
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

research-validate:
	uv run python tools/research.py validate

research-run:
	uv run python tools/research.py run experiments/specs/smoke.yaml

verify: check test research-validate
