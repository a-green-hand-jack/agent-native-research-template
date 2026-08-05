from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import phase_graph


def python_command(source: str) -> list[str]:
    return [sys.executable, "-c", source]


def two_phase_spec() -> dict[str, object]:
    generation = (
        "from pathlib import Path; "
        "Path('outputs').mkdir(exist_ok=True); "
        "Path('outputs/generated.txt').write_text('generated\\n')"
    )
    evaluation = (
        "import os; from pathlib import Path; "
        "source=Path(os.environ['RESEARCH_PHASE_GENERATION_ARTIFACT_DIR']); "
        "assert next(source.rglob('generated.txt')).read_text() == 'generated\\n'; "
        "Path('outputs/score.txt').write_text('1\\n')"
    )
    return {
        "assets": [],
        "phases": [
            {
                "id": "evaluation",
                "command": python_command(evaluation),
                "depends_on": ["generation"],
                "asset_phase": "evaluation",
                "outputs": [{"path": "outputs/score.txt", "required": True}],
            },
            {
                "id": "generation",
                "command": python_command(generation),
                "asset_phase": "generation",
                "outputs": [{"path": "outputs/generated.txt", "required": True}],
            },
        ],
    }


def execute(
    root: Path, run_id: str, spec: dict[str, object], **kwargs: object
) -> dict[str, object]:
    run_dir = root / "runs" / run_id
    run_dir.mkdir(parents=True)
    return phase_graph.execute_phases(
        spec,
        {},
        python_command("print('default')"),
        root,
        run_dir,
        os.environ.copy(),
        30,
        **kwargs,
    )


def test_topological_order_is_stable(tmp_path: Path) -> None:
    phases = phase_graph.normalize_phases(two_phase_spec(), ["ignored"])
    assert [phase["id"] for phase in phases] == ["generation", "evaluation"]


def test_cycle_is_rejected() -> None:
    spec = {
        "phases": [
            {"id": "a", "command": ["true"], "depends_on": ["b"]},
            {"id": "b", "command": ["true"], "depends_on": ["a"]},
        ]
    }
    with pytest.raises(phase_graph.PhaseGraphError, match="cycle"):
        phase_graph.normalize_phases(spec, ["ignored"])


def test_phases_write_terminal_results_and_snapshots(tmp_path: Path) -> None:
    result = execute(tmp_path, "parent-run", two_phase_spec())
    assert result["return_code"] == 0
    assert [record["status"] for record in result["phases"]] == ["succeeded", "succeeded"]
    for identifier in ("generation", "evaluation"):
        record_path = tmp_path / "runs/parent-run/phases" / identifier / "result.json"
        record = json.loads(record_path.read_text(encoding="utf-8"))
        assert record["status"] == "succeeded"
    assert any(
        artifact["source_path"] == "outputs/generated.txt" for artifact in result["artifacts"]
    )
    assert any(artifact["source_path"] == "outputs/score.txt" for artifact in result["artifacts"])


def test_phase_fails_closed_when_workload_mutates_protected_project_file(
    tmp_path: Path,
) -> None:
    source = tmp_path / "src/model.py"
    source.parent.mkdir(parents=True)
    source.write_text("original\n", encoding="utf-8")
    spec = {
        "assets": [],
        "phases": [
            {
                "id": "main",
                "command": python_command(
                    "from pathlib import Path; Path('src/model.py').write_text('changed\\n')"
                ),
                "asset_phase": "all",
                "outputs": [],
            }
        ],
    }

    result = execute(tmp_path, "mutating-run", spec)

    assert result["return_code"] == phase_graph.OUTPUT_CONTRACT_RETURN_CODE
    assert result["phases"][0]["status"] == "failed"
    assert result["phases"][0]["termination"] == {"reason": "protected_project_mutation"}
    assert result["phases"][0]["errors"] == ["protected project file changed: src/model.py"]


def test_failed_phase_marks_downstream_incomplete(tmp_path: Path) -> None:
    spec = two_phase_spec()
    spec["phases"][1]["command"] = python_command("raise SystemExit(2)")
    result = execute(tmp_path, "failed-run", spec)
    assert result["return_code"] == 2
    assert result["phases"][0]["status"] == "failed"
    assert result["phases"][1]["status"] == "incomplete"
    assert result["phases"][1]["termination"] == {"reason": "dependency_failed"}


def test_retry_phase_reuses_verified_upstream_artifacts(tmp_path: Path) -> None:
    spec = two_phase_spec()
    parent = execute(tmp_path, "parent-run", spec)
    parent_manifest = {"run_id": "parent-run", "phases": parent["phases"]}
    spec["phases"][1]["command"] = python_command("raise AssertionError('generation reran')")
    retry = execute(
        tmp_path,
        "retry-run",
        spec,
        retry_phase="evaluation",
        parent_manifest=parent_manifest,
    )
    assert retry["return_code"] == 0
    assert retry["phases"][0]["status"] == "reused"
    assert retry["phases"][0]["source_run_id"] == "parent-run"
    assert retry["phases"][1]["status"] == "succeeded"
    assert retry["recovery"]["generation_skipped"] is True
    assert retry["recovery"]["reused_artifacts"]


def test_missing_required_phase_output_fails_phase(tmp_path: Path) -> None:
    spec = {
        "assets": [],
        "phases": [
            {
                "id": "main",
                "command": python_command("print('no output')"),
                "outputs": [{"path": "outputs/missing.txt", "required": True}],
            }
        ],
    }
    result = execute(tmp_path, "output-failure", spec)
    assert result["return_code"] == phase_graph.OUTPUT_CONTRACT_RETURN_CODE
    assert result["phases"][0]["termination"] == {"reason": "output_contract_failed"}
