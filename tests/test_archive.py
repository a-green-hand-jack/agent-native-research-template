from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest
import yaml

TOOLS = Path(__file__).resolve().parents[1] / "tools"
SPEC = importlib.util.spec_from_file_location("archive_tool", TOOLS / "archive.py")
assert SPEC and SPEC.loader
archive = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(archive)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def install_schema(root: Path) -> None:
    source = Path(__file__).resolve().parents[1] / archive.SCHEMA_PATH
    destination = root / archive.SCHEMA_PATH
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def manifest(root: Path, *, reconstructable: bool = True) -> dict[str, object]:
    install_schema(root)
    copy = root / "archive/copy.bin"
    copy.parent.mkdir(parents=True)
    copy.write_bytes(b"evidence")
    sha = digest(copy)
    return {
        "schema_version": 1,
        "archive_id": "run-archive",
        "assets": [
            {
                "id": "run-evidence",
                "kind": "run_manifest",
                "sha256": sha,
                "reconstructable": reconstructable,
                "copies": [
                    {
                        "id": "local-copy",
                        "location": "archive/copy.bin",
                        "fault_domain": "local-disk",
                        "verification": {
                            "method": "local_readback",
                            "verified_at": "2026-08-03T00:00:00Z",
                            "sha256": sha,
                        },
                    }
                ],
            }
        ],
        "retirement_targets": [
            {
                "id": "old-worktree",
                "kind": "worktree",
                "required_asset_ids": ["run-evidence"],
            }
        ],
    }


def test_local_readback_verifies_reconstructable_asset(tmp_path: Path) -> None:
    result = archive.verify_archive(manifest(tmp_path), tmp_path)
    assert result["verified"] is True
    assert result["assets"][0]["verified_fault_domains"] == ["local-disk"]


def test_checksum_only_record_is_not_verified(tmp_path: Path) -> None:
    data = manifest(tmp_path)
    data["assets"][0]["copies"][0]["verification"].pop("verified_at")
    with pytest.raises(archive.ArchiveError, match="schema"):
        archive.verify_archive(data, tmp_path)


def test_local_readback_detects_corruption(tmp_path: Path) -> None:
    data = manifest(tmp_path)
    (tmp_path / "archive/copy.bin").write_bytes(b"corrupt")
    result = archive.verify_archive(data, tmp_path)
    assert result["verified"] is False
    assert "checksum mismatch" in result["assets"][0]["copies"][0]["reason"]


def test_external_evidence_requires_more_than_a_checksum(tmp_path: Path) -> None:
    data = manifest(tmp_path)
    verification = data["assets"][0]["copies"][0]["verification"]
    verification["method"] = "external_evidence"
    data["assets"][0]["copies"][0]["location"] = "s3://archive/run"
    result = archive.verify_archive(data, tmp_path)
    assert result["verified"] is False
    assert "non-empty evidence" in result["assets"][0]["copies"][0]["reason"]


def test_non_reconstructable_asset_requires_two_fault_domains(tmp_path: Path) -> None:
    data = manifest(tmp_path, reconstructable=False)
    result = archive.verify_archive(data, tmp_path)
    assert result["verified"] is False
    assert "requires 2 verified independent" in result["blockers"][0]


def test_two_independent_verified_copies_allow_retirement(tmp_path: Path) -> None:
    data = manifest(tmp_path, reconstructable=False)
    asset = data["assets"][0]
    asset["copies"].append(
        {
            "id": "remote-copy",
            "location": "object://secondary/run",
            "fault_domain": "remote-object-store",
            "verification": {
                "method": "external_evidence",
                "verified_at": "2026-08-03T00:01:00Z",
                "sha256": asset["sha256"],
                "evidence": "provider read-back job 42 completed",
            },
        }
    )
    result = archive.retirement_preflight(data, tmp_path)
    assert result["targets"][0]["decision"] == "allow"
    assert result["destructive_action_performed"] is False


def test_unique_untracked_assets_block_retirement(tmp_path: Path) -> None:
    data = manifest(tmp_path)
    data["retirement_targets"][0]["unique_untracked_paths"] = ["outputs/only-copy.bin"]
    result = archive.retirement_preflight(data, tmp_path)
    assert result["targets"][0]["decision"] == "block"
    assert "unique untracked paths" in result["targets"][0]["blockers"][0]


def test_cli_outputs_machine_readable_decision(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = manifest(tmp_path)
    path = tmp_path / "archive.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    code = archive.main(["retirement-preflight", "archive.yaml"], tmp_path)
    assert code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["targets"][0]["decision"] == "allow"
    assert output["stop_delete_retire_are_separate"] is True
