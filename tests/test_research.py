from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "research.py"
SPEC = importlib.util.spec_from_file_location("research_tool", MODULE_PATH)
assert SPEC and SPEC.loader
research = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(research)


def build_repository(root: Path) -> Path:
    files = {
        "CONTRIBUTIONS.md": (
            "| ID | Contribution | Code | Parameters | Evidence | Status |\n"
            "|---|---|---|---|---|---|\n"
            "| bootstrap | Demo | `src/` | `configs/base.yaml` | `evals/smoke.yaml` | bootstrap |\n"
        ),
        "configs/base.yaml": "seed: 0\n",
        "environments/main.yaml": "id: main\nlockfile: uv.lock\n",
        "evals/smoke.yaml": "id: smoke\ncommand: make smoke\n",
        "infra/profiles/local.yaml": "id: local\nexecutor: local\n",
        "uv.lock": "version = 1\n",
        "Makefile": ".PHONY: smoke\nsmoke:\n\t@printf 'ok\\n'\n",
        "experiments/specs/smoke.yaml": (
            "id: smoke\n"
            "question: Does the smoke path work?\n"
            "contribution: bootstrap\n"
            "config: configs/base.yaml\n"
            "environment: main\n"
            "executor: local\n"
            "evaluation: smoke\n"
            "command: make smoke\n"
            "seed_policy:\n  mode: fixed\n  seeds: [0]\n"
            "budget:\n  kind: smoke\n  max_runs: 1\n"
            "stopping_rule: Stop after one attempt.\n"
            "inclusion_criteria: Include every attempt.\n"
        ),
    }
    for relative_name, content in files.items():
        path = root / relative_name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return root / "experiments/specs/smoke.yaml"


def test_validate_smoke_spec(tmp_path: Path) -> None:
    spec_path = build_repository(tmp_path)
    resolved = research.validate_spec(spec_path, tmp_path)
    assert resolved["spec"]["id"] == "smoke"
    assert resolved["argv"] == ["make", "smoke"]


def test_validate_rejects_unknown_contribution(tmp_path: Path) -> None:
    spec_path = build_repository(tmp_path)
    text = spec_path.read_text(encoding="utf-8").replace(
        "contribution: bootstrap", "contribution: missing"
    )
    spec_path.write_text(text, encoding="utf-8")
    with pytest.raises(research.SpecError, match="unknown contribution"):
        research.validate_spec(spec_path, tmp_path)


def test_run_and_promote_manifest(tmp_path: Path) -> None:
    spec_path = build_repository(tmp_path)
    manifest_path, return_code = research.run_experiment(spec_path, tmp_path)
    assert return_code == 0
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "succeeded"
    assert manifest["spec"]["sha256"]
    assert manifest["environment"]["lockfile_sha256"]

    promoted = research.promote_manifest(manifest["run_id"], tmp_path)
    assert promoted.is_file()
    assert json.loads(promoted.read_text(encoding="utf-8"))["run_id"] == manifest["run_id"]
