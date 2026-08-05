from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

SPEC = importlib.util.spec_from_file_location("evidence_tool", TOOLS / "evidence.py")
assert SPEC and SPEC.loader
evidence = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evidence)

from test_research import build_repository


def configure_outputs(root: Path) -> Path:
    spec = build_repository(root)
    (root / "src/test_project/workloads.py").write_text(
        "from __future__ import annotations\n\n"
        "import json\n"
        "import os\n"
        "from pathlib import Path\n\n"
        "def main(argv: list[str] | None = None) -> int:\n"
        "    assert argv == ['smoke']\n"
        "    output = Path('outputs/metrics.json')\n"
        "    output.parent.mkdir(parents=True, exist_ok=True)\n"
        "    output.write_text(json.dumps({'score': 0.75}), encoding='utf-8')\n"
        "    print(f\"accuracy=0.75 seed={os.environ['RESEARCH_SEED']}\")\n"
        "    return 0\n",
        encoding="utf-8",
    )
    (root / "evals/smoke.yaml").write_text(
        "schema_version: 1\nid: smoke\n"
        "purpose: execute the smallest path\nmetrics:\n"
        "  - id: success\n    type: boolean\n    direction: maximize\n"
        "    unit: boolean\n    aggregation: single\n"
        "    resource_mode: single_process\n    sample_count: 1\n"
        "    observation_count: 1\n    source:\n      type: return_code\n"
        "  - id: accuracy\n    type: number\n    direction: maximize\n"
        "    unit: fraction\n    aggregation: single\n"
        "    resource_mode: single_process\n    sample_count: 1\n"
        "    observation_count: 1\n    source:\n"
        "      type: stdout_regex\n      pattern: 'accuracy=([0-9.]+)'\n"
        "  - id: score\n    type: number\n    direction: maximize\n"
        "    unit: fraction\n    aggregation: single\n"
        "    resource_mode: single_process\n    sample_count: 1\n"
        "    observation_count: 1\n    source:\n      type: json_file\n"
        "      path: outputs/metrics.json\n      key: score\n",
        encoding="utf-8",
    )
    text = spec.read_text(encoding="utf-8").replace(
        "artifacts: []",
        "artifacts:\n  - path: outputs/metrics.json\n    required: true",
    )
    spec.write_text(text, encoding="utf-8")
    return spec


def artifact_snapshot(manifest: dict[str, object]) -> dict[str, str]:
    artifacts = manifest["artifacts"]
    assert isinstance(artifacts, list)
    for artifact in artifacts:
        if isinstance(artifact, dict) and artifact.get("source_path") == "outputs/metrics.json":
            return artifact
    raise AssertionError("declared artifact snapshot was not recorded")


def install_strict_artifact_schema(root: Path) -> None:
    path = root / evidence.research.SCHEMA_DOCUMENTS["run manifest"]
    path.write_text(
        json.dumps(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "title": "Strict Run Manifest",
                "type": "object",
                "x-schema-version": 1,
                "required": ["artifacts"],
                "properties": {
                    "artifacts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["path", "sha256"],
                            "properties": {
                                "path": {"type": "string", "minLength": 1},
                                "sha256": {
                                    "type": "string",
                                    "pattern": "^[a-f0-9]{64}$",
                                },
                            },
                        },
                    }
                },
            }
        ),
        encoding="utf-8",
    )


def test_run_extracts_metrics_and_snapshots_declared_artifacts(tmp_path: Path) -> None:
    spec = configure_outputs(tmp_path)
    manifest_path, code = evidence.run_spec(spec, tmp_path)
    assert code == 0
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["metrics"]["accuracy"]["value"] == 0.75
    assert manifest["metrics"]["score"]["value"] == 0.75
    assert manifest["metrics"]["success"]["value"] is True
    assert manifest["seed"] == 0
    assert manifest["seed_environment_variable"] == "RESEARCH_SEED"
    assert manifest["termination"] == {"reason": "completed"}
    snapshot = artifact_snapshot(manifest)
    assert snapshot["path"].startswith(f"runs/{manifest['run_id']}/artifacts/")
    assert (tmp_path / snapshot["path"]).read_text(encoding="utf-8") == '{"score": 0.75}'
    assert manifest["evaluation_errors"] == []


def test_verify_run_uses_snapshot_after_source_is_overwritten(tmp_path: Path) -> None:
    spec = configure_outputs(tmp_path)
    manifest_path, _ = evidence.run_spec(spec, tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    (tmp_path / "outputs/metrics.json").write_text("{}", encoding="utf-8")
    assert evidence.verify_run(manifest["run_id"], tmp_path)["run_id"] == manifest["run_id"]


def test_verify_run_detects_snapshot_tampering(tmp_path: Path) -> None:
    spec = configure_outputs(tmp_path)
    manifest_path, _ = evidence.run_spec(spec, tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    snapshot = artifact_snapshot(manifest)
    (tmp_path / snapshot["path"]).write_text("{}", encoding="utf-8")
    with pytest.raises(evidence.EvidenceError, match="checksum mismatch"):
        evidence.verify_run(manifest["run_id"], tmp_path)


def test_verify_run_rejects_schema_invalid_manifest(tmp_path: Path) -> None:
    spec = configure_outputs(tmp_path)
    install_strict_artifact_schema(tmp_path)
    manifest_path, _ = evidence.run_spec(spec, tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifacts"][0]["sha256"] = "not-a-sha256"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(evidence.research.SpecError, match="does not match run manifest schema"):
        evidence.verify_run(manifest["run_id"], tmp_path)


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ("seeds: [0]", "seeds: [0, 1]", "exactly one fixed seed"),
        ("max_runs: 1", "max_runs: 2", "exactly one execution"),
        (
            "type: after_runs\n  runs: 1",
            "type: metric_threshold\n  metric: success\n  operator: '=='\n  value: 1",
            "supports only stopping_rule",
        ),
    ],
)
def test_local_runner_rejects_unsupported_controls(
    tmp_path: Path,
    old: str,
    new: str,
    message: str,
) -> None:
    spec = configure_outputs(tmp_path)
    spec.write_text(spec.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")
    with pytest.raises(evidence.EvidenceError, match=message):
        evidence.run_spec(spec, tmp_path)
    assert not (tmp_path / "runs").exists()


def test_local_runner_enforces_wall_time_budget(tmp_path: Path) -> None:
    spec = build_repository(tmp_path)
    (tmp_path / "src/test_project/workloads.py").write_text(
        "import time\n\ndef main(argv=None):\n    time.sleep(2)\n    return 0\n",
        encoding="utf-8",
    )
    text = spec.read_text(encoding="utf-8").replace(
        "max_wall_time_seconds: 60",
        "max_wall_time_seconds: 1",
    )
    spec.write_text(text, encoding="utf-8")
    manifest_path, code = evidence.run_spec(spec, tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert code == evidence.TIMEOUT_RETURN_CODE
    assert manifest["status"] == "failed"
    assert manifest["termination"] == {
        "reason": "timeout",
        "max_wall_time_seconds": 1,
    }


def test_local_runner_records_protected_project_mutation_as_failure(tmp_path: Path) -> None:
    spec = build_repository(tmp_path)
    (tmp_path / "src/test_project/workloads.py").write_text(
        "from pathlib import Path\n\n"
        "def main(argv=None):\n"
        "    Path('configs/base.yaml').write_text('seed: 9\\n', encoding='utf-8')\n"
        "    return 0\n",
        encoding="utf-8",
    )

    manifest_path, code = evidence.run_spec(spec, tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert code == evidence.phase_graph.OUTPUT_CONTRACT_RETURN_CODE
    assert manifest["status"] == "failed"
    assert manifest["termination"] == {"reason": "protected_project_mutation"}
    assert manifest["phases"][0]["errors"] == ["protected project file changed: configs/base.yaml"]


def test_parent_run_is_recorded(tmp_path: Path) -> None:
    spec = configure_outputs(tmp_path)
    first_path, _ = evidence.run_spec(spec, tmp_path)
    first = json.loads(first_path.read_text(encoding="utf-8"))
    second_path, _ = evidence.run_spec(spec, tmp_path, parent_run_id=first["run_id"])
    second = json.loads(second_path.read_text(encoding="utf-8"))
    assert second["parent_run_id"] == first["run_id"]


def test_replay_rejects_input_drift(tmp_path: Path) -> None:
    spec = configure_outputs(tmp_path)
    manifest_path, _ = evidence.run_spec(spec, tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    (tmp_path / "configs/base.yaml").write_text("seed: 1\n", encoding="utf-8")
    with pytest.raises(evidence.EvidenceError, match="inputs drifted"):
        evidence.replay_run(manifest["run_id"], tmp_path)


def test_replay_links_new_run_to_parent(tmp_path: Path) -> None:
    spec = configure_outputs(tmp_path)
    manifest_path, _ = evidence.run_spec(spec, tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    replay_path, code = evidence.replay_run(manifest["run_id"], tmp_path)
    replay = json.loads(replay_path.read_text(encoding="utf-8"))
    assert code == 0
    assert replay["parent_run_id"] == manifest["run_id"]


def test_promote_records_review_and_source_hash(tmp_path: Path) -> None:
    spec = configure_outputs(tmp_path)
    manifest_path, _ = evidence.run_spec(spec, tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    promoted = evidence.promote_manifest(
        manifest["run_id"],
        tmp_path,
        decision="accepted",
        note="Reviewed smoke evidence.",
    )
    envelope = json.loads(promoted.read_text(encoding="utf-8"))
    assert envelope["review"]["decision"] == "accepted"
    assert envelope["review"]["note"] == "Reviewed smoke evidence."
    assert envelope["source"]["sha256"] == evidence.research.sha256_file(manifest_path)
