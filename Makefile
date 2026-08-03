.PHONY: setup hooks check format test smoke project-check template-compat ci-policy control-cli research-validate research-run template-e2e verify

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

template-compat:
	uv run python tools/template_compat.py check

ci-policy:
	uv run python tools/ci_policy.py

control-cli:
	uv run researchctl --help >/dev/null
	uv run researchctl experiment plan experiments/specs/smoke.yaml >/dev/null

research-validate:
	uv run researchctl experiment validate

research-run:
	uv run researchctl experiment run experiments/specs/smoke.yaml

template-e2e:
	uv run python tools/verify_template_e2e.py

verify: check test project-check template-compat ci-policy control-cli research-validate
