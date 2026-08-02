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
    (root / "Makefile").write_text(
        ".PHONY: smoke\nsmoke:\n"
        "\t@mkdir -p outputs\n"
        "\t@printf '{\"score\": 0.75}' > outputs/metrics.json\n"
        "\t@printf 'accuracy=0.75 seed=%s\\n' \"$$RESEARCH_SEED\"\n",
        encoding="utf-8",
    )
    (root / "evals/smoke.yaml").write_text(
        "schema_version: 1\nid: smoke\ncommand: make smoke\n"
        "purpose: execute the smallest path\nmetrics:\n"
        "  - id: success\n    type: boolean\n    direction: maximize\n"
        "    source:\n      type: return_code\n"
        "  - id: accuracy\n    type: number\n    direction: maximize\n"
        "    source:\n      type: stdout_regex\n      pattern: 'accuracy=([0-9.]+)'\n"
        "  - id: score\n    type: number\n    direction: maximize\n"
        "    source:\n      type: json_file\n      path: outputs/metrics.json\n      key: score\n",
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


def test_run_extracts_metrics_and_snapshots_declared_artifacts(tmp_path: Path) -> None:
    spec = configure_outputs(tmp_path)
    manifest_path, code = evidence.run_spec(spec, tmp_path)
    assert code == 0
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["metrics"] == {"accuracy": 0.75, "score": 0.75, "success": True}
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
    (tmp_path / "Makefile").write_text(
        ".PHONY: smoke\nsmoke:\n\t@python -c 'import time; time.sleep(2)'\n",
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
