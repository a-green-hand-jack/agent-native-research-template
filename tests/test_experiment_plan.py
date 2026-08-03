from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

SPEC = importlib.util.spec_from_file_location("experiment_plan_tool", TOOLS / "experiment_plan.py")
assert SPEC and SPEC.loader
plan_tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(plan_tool)

from test_research import build_repository


def enrich_spec(path: Path, **updates: object) -> None:
    spec = yaml.safe_load(path.read_text(encoding="utf-8"))
    spec.update(updates)
    path.write_text(yaml.safe_dump(spec, sort_keys=False), encoding="utf-8")


def test_plan_is_stable_across_yaml_key_order(tmp_path: Path) -> None:
    spec_path = build_repository(tmp_path)
    enrich_spec(
        spec_path,
        protocol_id="smoke-v1",
        run_class="pilot",
        scientific_parameters={"temperature": 0.2, "beam": 4},
    )
    first = plan_tool.plan_spec(spec_path, tmp_path)
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    reversed_spec = dict(reversed(list(spec.items())))
    spec_path.write_text(yaml.safe_dump(reversed_spec, sort_keys=False), encoding="utf-8")
    second = plan_tool.plan_spec(spec_path, tmp_path)
    assert first == second
    assert first["sha256"] == plan_tool.sha256_json(first["resolved"])


def test_config_content_changes_plan_identity(tmp_path: Path) -> None:
    spec_path = build_repository(tmp_path)
    first = plan_tool.plan_spec(spec_path, tmp_path)
    (tmp_path / "configs/base.yaml").write_text("seed: 1\n", encoding="utf-8")
    second = plan_tool.plan_spec(spec_path, tmp_path)
    assert first["sha256"] != second["sha256"]
    assert second["resolved"]["effective_config"]["resolved"] == {"seed": 1}


def test_matrix_expansion_has_stable_cell_ids(tmp_path: Path) -> None:
    spec_path = build_repository(tmp_path)
    enrich_spec(
        spec_path,
        protocol_id="matrix-v1",
        run_class="pilot",
        scientific_parameters={"dataset": "tiny"},
        matrix={"seed_variant": [0, 1], "temperature": [0.1, 0.2]},
    )
    plan = plan_tool.plan_spec(spec_path, tmp_path)["resolved"]
    assert [cell["parameters"] for cell in plan["cells"]] == [
        {"dataset": "tiny", "seed_variant": 0, "temperature": 0.1},
        {"dataset": "tiny", "seed_variant": 0, "temperature": 0.2},
        {"dataset": "tiny", "seed_variant": 1, "temperature": 0.1},
        {"dataset": "tiny", "seed_variant": 1, "temperature": 0.2},
    ]
    assert len({cell["cell_id"] for cell in plan["cells"]}) == 4


def test_duplicate_matrix_values_are_rejected(tmp_path: Path) -> None:
    spec_path = build_repository(tmp_path)
    enrich_spec(spec_path, matrix={"temperature": [0.1, 0.1]})
    with pytest.raises(plan_tool.PlanError, match="duplicate values"):
        plan_tool.plan_spec(spec_path, tmp_path)


def test_formal_run_requires_explicit_pre_observation_protocol(tmp_path: Path) -> None:
    spec_path = build_repository(tmp_path)
    enrich_spec(spec_path, run_class="formal")
    with pytest.raises(plan_tool.PlanError, match="explicit protocol_id"):
        plan_tool.plan_spec(spec_path, tmp_path)
    enrich_spec(
        spec_path,
        protocol_id="formal-v1",
        observation_status="post_observation",
    )
    with pytest.raises(plan_tool.PlanError, match="pre_observation"):
        plan_tool.plan_spec(spec_path, tmp_path)


def test_post_observation_run_is_explicit(tmp_path: Path) -> None:
    spec_path = build_repository(tmp_path)
    enrich_spec(
        spec_path,
        protocol_id="analysis-v2",
        run_class="post_observation",
        observation_status="post_observation",
    )
    plan = plan_tool.plan_spec(spec_path, tmp_path)["resolved"]
    assert plan["run_class"] == "post_observation"
    assert plan["observation_status"] == "post_observation"


def test_planning_does_not_execute_experiment_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec_path = build_repository(tmp_path)

    def reject_execution(*_: object, **__: object) -> subprocess.CompletedProcess[str]:
        raise AssertionError("planning must not execute subprocesses")

    monkeypatch.setattr(subprocess, "run", reject_execution)
    monkeypatch.setattr(
        plan_tool.research,
        "git_state",
        lambda _root: {
            "commit": None,
            "dirty": False,
            "status": [],
            "patch_sha256": "0" * 64,
        },
    )
    rendered = plan_tool.render_plan(spec_path, tmp_path)
    document = json.loads(rendered)
    assert document["resolved"]["phases"][0]["command"] == ["make", "smoke"]
