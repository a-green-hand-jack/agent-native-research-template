.PHONY: setup hooks check format test smoke project-check template-compat ci-policy control-cli research-validate research-run template-test template-e2e verify

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
	uv run researchctl project check

template-compat:
	uv run researchctl project compatibility

ci-policy:
	uv run python tools/ci_policy.py

control-cli:
	uv run researchctl --help >/dev/null
	uv run researchctl experiment plan experiments/specs/smoke.yaml >/dev/null

research-validate:
	uv run researchctl experiment validate

research-run:
	uv run researchctl experiment run experiments/specs/smoke.yaml

template-test:
	uv run pytest -q template/tests

template-e2e:
	uv run python template/verify_downstream.py

verify: check test template-test project-check template-compat ci-policy control-cli research-validate
