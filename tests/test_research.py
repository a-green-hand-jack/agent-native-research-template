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


def schema_document(title: str) -> str:
    return json.dumps(
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": title,
            "type": "object",
            "x-schema-version": 1,
        }
    )


def build_repository(root: Path, *, nested: bool = True) -> Path:
    spec_name = "experiments/specs/smoke/basic.yaml" if nested else "experiments/specs/smoke.yaml"
    files = {
        "PROJECT.yaml": (
            "schema_version: 1\ninitialized: true\nproject_name: Test Project\n"
            "distribution_name: test-project\npackage_name: test_project\n"
            "cli_name: researchctl\ncontribution_id: bootstrap\n"
            "template:\n  name: agent-native-research-template\n  version: 7\n"
            "  initialized_from_commit: test\n  reviewed_template_commit: test\n"
            "  applied_migrations: []\n"
        ),
        "CONTRIBUTIONS.md": (
            "| ID | Contribution | Code | Parameters | Evidence | Status |\n"
            "|---|---|---|---|---|---|\n"
            "| bootstrap | Demo | `src/` | `configs/base.yaml` | `evals/smoke.yaml` | bootstrap |\n"
        ),
        "configs/base.yaml": "seed: 0\n",
        "environments/main.yaml": (
            "schema_version: 1\nid: main\nbackend: uv\nlockfile: uv.lock\n"
            "purpose: test environment\n"
        ),
        "evals/smoke.yaml": (
            "schema_version: 1\nid: smoke\n"
            "purpose: execute the smallest path\nmetrics:\n"
            "  - id: success\n    type: boolean\n    direction: maximize\n"
            "    unit: boolean\n    aggregation: single\n"
            "    resource_mode: single_process\n    sample_count: 1\n"
            "    observation_count: 1\n    source:\n      type: return_code\n"
        ),
        "infra/profiles/local.yaml": (
            "schema_version: 1\nid: local\nexecutor: local\ncapabilities: [cpu]\n"
            "environment: {PYTHONUNBUFFERED: '1'}\n"
            "inherit_environment: [PATH, HOME]\n"
        ),
        "uv.lock": "version = 1\n",
        "Makefile": ".PHONY: smoke\nsmoke:\n\t@printf 'ok\\n'\n",
        "src/test_project/__init__.py": "",
        "src/test_project/workloads.py": (
            "from __future__ import annotations\n\n"
            "import argparse\n\n"
            "def main(argv: list[str] | None = None) -> int:\n"
            "    parser = argparse.ArgumentParser()\n"
            "    parser.add_subparsers(dest='command', required=True).add_parser('smoke')\n"
            "    parser.parse_args(argv)\n"
            "    print('ok')\n"
            "    return 0\n"
        ),
        spec_name: (
            "schema_version: 1\nid: smoke\nquestion: Does the smoke path work?\n"
            "contribution: bootstrap\nconfig: configs/base.yaml\nenvironment: main\n"
            "executor: local\nevaluation: smoke\n"
            "command: [researchctl, workload, smoke]\n"
            "seed_policy:\n  mode: fixed\n  seeds: [0]\n"
            "budget:\n  max_runs: 1\n  max_wall_time_seconds: 60\n"
            "stopping_rule:\n  type: after_runs\n  runs: 1\n"
            "inclusion_criteria:\n  - Include every completed attempt.\n"
            "artifacts: []\n"
        ),
    }
    for relative_path in research.SCHEMA_DOCUMENTS.values():
        files[relative_path] = schema_document(relative_path)
    for relative_name, content in files.items():
        path = root / relative_name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return root / spec_name


def test_validate_recursively_discovers_specs(tmp_path: Path) -> None:
    spec_path = build_repository(tmp_path)
    paths = research.validate_all(tmp_path)
    assert paths == [spec_path]
    resolved = research.validate_spec(spec_path, tmp_path)
    assert resolved["spec"]["id"] == "smoke"
    assert resolved["argv"] == ["researchctl", "workload", "smoke"]


def test_validate_rejects_free_form_experiment_command(tmp_path: Path) -> None:
    spec_path = build_repository(tmp_path)
    spec_path.write_text(
        spec_path.read_text(encoding="utf-8").replace(
            "command: [researchctl, workload, smoke]", "command: make smoke"
        ),
        encoding="utf-8",
    )
    with pytest.raises(research.SpecError, match="structured argv"):
        research.validate_spec(spec_path, tmp_path)


def test_validate_rejects_command_outside_configured_workload_cli(tmp_path: Path) -> None:
    spec_path = build_repository(tmp_path)
    spec_path.write_text(
        spec_path.read_text(encoding="utf-8").replace(
            "[researchctl, workload, smoke]", "[python, internal.py]"
        ),
        encoding="utf-8",
    )
    with pytest.raises(research.SpecError, match="researchctl workload"):
        research.validate_spec(spec_path, tmp_path)


def test_validate_rejects_duplicate_experiment_ids(tmp_path: Path) -> None:
    spec_path = build_repository(tmp_path)
    duplicate = tmp_path / "experiments/specs/other/duplicate.yaml"
    duplicate.parent.mkdir(parents=True)
    duplicate.write_text(spec_path.read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(research.SpecError, match="duplicate experiment ID"):
        research.validate_all(tmp_path)


def test_validate_rejects_invalid_metric_direction(tmp_path: Path) -> None:
    build_repository(tmp_path)
    evaluation = tmp_path / "evals/smoke.yaml"
    evaluation.write_text(
        evaluation.read_text(encoding="utf-8").replace("maximize", "up"),
        encoding="utf-8",
    )
    with pytest.raises(research.SpecError, match="direction"):
        research.validate_all(tmp_path)


def test_validate_enforces_json_schema_nested_fields(tmp_path: Path) -> None:
    build_repository(tmp_path)
    schema_path = tmp_path / research.SCHEMA_DOCUMENTS["evaluation"]
    schema_path.write_text(
        json.dumps(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "title": "Strict Evaluation",
                "type": "object",
                "x-schema-version": 1,
                "properties": {
                    "metrics": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "source": {
                                    "type": "object",
                                    "properties": {"type": {"const": "return_code"}},
                                    "additionalProperties": False,
                                }
                            },
                        },
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    evaluation = tmp_path / "evals/smoke.yaml"
    evaluation.write_text(
        evaluation.read_text(encoding="utf-8").replace(
            "type: return_code",
            "type: return_code\n      pattern: ignored",
        ),
        encoding="utf-8",
    )
    with pytest.raises(research.SpecError, match="does not match evaluation schema"):
        research.validate_all(tmp_path)


def test_validate_rejects_duplicate_command_sources(tmp_path: Path) -> None:
    spec_path = build_repository(tmp_path)
    text = spec_path.read_text(encoding="utf-8")
    spec_path.write_text(
        text + "phases:\n  - id: main\n" + "    command: [researchctl, workload, smoke]\n",
        encoding="utf-8",
    )
    with pytest.raises(research.SpecError, match="exactly one of command or phases"):
        research.validate_all(tmp_path)


def test_validate_rejects_unversioned_definition(tmp_path: Path) -> None:
    build_repository(tmp_path)
    environment = tmp_path / "environments/main.yaml"
    environment.write_text(
        environment.read_text(encoding="utf-8").replace("schema_version: 1\n", ""),
        encoding="utf-8",
    )
    with pytest.raises(research.SpecError, match="schema_version"):
        research.validate_all(tmp_path)


def test_research_tool_has_validation_only_surface(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert not hasattr(research, "run_experiment")
    assert not hasattr(research, "promote_manifest")
    for command in ("run", "promote"):
        with pytest.raises(SystemExit) as exc_info:
            research.build_parser().parse_args([command, "value"])
        assert exc_info.value.code == 2
        assert "invalid choice" in capsys.readouterr().err
