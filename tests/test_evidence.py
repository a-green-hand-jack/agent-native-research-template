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
        "\t@printf 'accuracy=0.75\\n'\n",
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
        "artifacts: []", "artifacts:\n  - path: outputs/metrics.json\n    required: true"
    )
    spec.write_text(text, encoding="utf-8")
    return spec


def test_run_extracts_metrics_and_declared_artifacts(tmp_path: Path) -> None:
    spec = configure_outputs(tmp_path)
    manifest_path, code = evidence.run_spec(spec, tmp_path)
    assert code == 0
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["metrics"] == {"accuracy": 0.75, "score": 0.75, "success": True}
    assert any(item["path"] == "outputs/metrics.json" for item in manifest["artifacts"])
    assert manifest["evaluation_errors"] == []


def test_verify_run_detects_artifact_tampering(tmp_path: Path) -> None:
    spec = configure_outputs(tmp_path)
    manifest_path, _ = evidence.run_spec(spec, tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    (tmp_path / "outputs/metrics.json").write_text("{}", encoding="utf-8")
    with pytest.raises(evidence.EvidenceError, match="checksum mismatch"):
        evidence.verify_run(manifest["run_id"], tmp_path)


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
