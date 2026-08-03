from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_evidence import configure_outputs

import evidence


def add_inputs(spec: Path) -> None:
    spec.write_text(
        spec.read_text(encoding="utf-8").replace(
            "seed_policy:",
            "inputs:\n"
            "  - id: source-tree\n"
            "    kind: path\n"
            "    path: src\n"
            "  - id: benchmark-release\n"
            "    kind: uri\n"
            "    uri: https://example.invalid/releases/1\n"
            "    version: '1'\n"
            "  - id: private-split\n"
            "    kind: opaque\n"
            "    value: split-2026-08\n"
            "seed_policy:",
        ),
        encoding="utf-8",
    )


def test_run_records_resolved_input_identities(tmp_path: Path) -> None:
    spec = configure_outputs(tmp_path)
    (tmp_path / "src").mkdir()
    (tmp_path / "src/model.py").write_text("VALUE = 1\n", encoding="utf-8")
    add_inputs(spec)
    manifest_path, code = evidence.run_spec(spec, tmp_path)
    assert code == 0
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert [record["id"] for record in manifest["inputs"]] == [
        "source-tree",
        "benchmark-release",
        "private-split",
    ]
    path_record = manifest["inputs"][0]
    assert path_record["path"] == "src"
    assert path_record["path_type"] == "directory"
    assert path_record["file_count"] == 1
    assert len(path_record["sha256"]) == 64


def test_replay_rejects_path_input_drift(tmp_path: Path) -> None:
    spec = configure_outputs(tmp_path)
    (tmp_path / "src").mkdir()
    source = tmp_path / "src/model.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    add_inputs(spec)
    manifest_path, _ = evidence.run_spec(spec, tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source.write_text("VALUE = 2\n", encoding="utf-8")
    with pytest.raises(evidence.EvidenceError, match="input source-tree changed"):
        evidence.replay_run(manifest["run_id"], tmp_path)
