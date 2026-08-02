.PHONY: setup hooks check format test smoke project-check research-validate research-run verify

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

project-check:
	uv run python tools/initialize_project.py check

research-validate:
	uv run python tools/research.py validate
	uv run python tools/evidence.py validate

research-run:
	uv run python tools/evidence.py run experiments/specs/smoke.yaml

verify: check test project-check research-validate
