from __future__ import annotations

import json
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import run_state
from test_evidence import configure_outputs

import evidence


def test_run_writes_atomic_terminal_result(tmp_path: Path) -> None:
    spec_path = configure_outputs(tmp_path)
    manifest_path, code = evidence.run_spec(spec_path, tmp_path)
    assert code == 0
    result_path = manifest_path.parent / "result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result["state"] == "succeeded"
    assert result["terminal"] is True
    assert result["manifest_sha256"] == evidence.research.sha256_file(manifest_path)
    assert not result_path.with_suffix(".json.tmp").exists()


def test_status_and_results_are_read_only_json(tmp_path: Path) -> None:
    spec_path = configure_outputs(tmp_path)
    manifest_path, _ = evidence.run_spec(spec_path, tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    status = evidence.run_status(manifest["run_id"], tmp_path)
    results = evidence.run_results(manifest["run_id"], tmp_path)
    assert status["state"] == "succeeded"
    assert results["status"]["state"] == "succeeded"
    assert results["metrics"]["success"] is True


def test_verify_returns_verified_projection_without_mutation(tmp_path: Path) -> None:
    spec_path = configure_outputs(tmp_path)
    manifest_path, _ = evidence.run_spec(spec_path, tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    result_path = manifest_path.parent / "result.json"
    before = result_path.read_text(encoding="utf-8")
    verified = evidence.verified_status(manifest["run_id"], tmp_path)
    after = result_path.read_text(encoding="utf-8")
    assert verified["state"] == "verified"
    assert verified["verified_state"] == "succeeded"
    assert before == after


def test_tampered_result_manifest_hash_is_rejected(tmp_path: Path) -> None:
    spec_path = configure_outputs(tmp_path)
    manifest_path, _ = evidence.run_spec(spec_path, tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    result_path = manifest_path.parent / "result.json"
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["manifest_sha256"] = "0" * 64
    result_path.write_text(json.dumps(result), encoding="utf-8")
    try:
        evidence.verify_run(manifest["run_id"], tmp_path)
    except evidence.EvidenceError as exc:
        assert "terminal result manifest checksum mismatch" in str(exc)
    else:
        raise AssertionError("tampered terminal result was accepted")


def test_missing_terminal_result_is_incomplete(tmp_path: Path) -> None:
    run_dir = tmp_path / "runs/manual"
    run_dir.mkdir(parents=True)
    run_state.write_progress(run_dir, "running", phase="main")
    status = evidence.run_status("manual", tmp_path)
    assert status["state"] == "running"
    assert status["terminal"] is False
