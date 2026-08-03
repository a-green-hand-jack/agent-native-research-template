from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import archive


def build_repository(root: Path, *, include_private_asset: bool = True) -> Path:
    schema_source = archive.ROOT / archive.ARCHIVE_SCHEMA
    schema_target = root / archive.ARCHIVE_SCHEMA
    schema_target.parent.mkdir(parents=True, exist_ok=True)
    schema_target.write_text(schema_source.read_text(encoding="utf-8"), encoding="utf-8")

    run_dir = root / "runs/run-1"
    artifact = run_dir / "artifacts/output.txt"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("result\n", encoding="utf-8")
    assets: list[dict[str, object]] = []
    if include_private_asset:
        private = root / "datasets/private.bin"
        private.parent.mkdir(parents=True, exist_ok=True)
        private.write_bytes(b"private-data")
        assets.append(
            {
                "id": "private-dataset",
                "kind": "path",
                "scope": "repository",
                "path": "datasets/private.bin",
                "path_type": "file",
                "access": "read",
                "exists": True,
                "sha256": archive.sha256_file(private),
                "file_count": 1,
                "reconstructable": False,
            }
        )
    manifest = {
        "run_id": "run-1",
        "artifacts": [
            {
                "path": "runs/run-1/artifacts/output.txt",
                "sha256": archive.sha256_file(artifact),
            }
        ],
        "asset_bindings": {"assets": assets},
    }
    manifest_path = run_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def test_two_fault_domains_verify_non_reconstructable_asset(tmp_path: Path) -> None:
    build_repository(tmp_path)
    archive_path = archive.create_archive(
        "run-1",
        tmp_path,
        copies=[
            (tmp_path / "copies-a", "region-a"),
            (tmp_path / "copies-b", "region-b"),
        ],
    )
    report = archive.verify_archive(archive_path, tmp_path)
    assert report["valid"] is True
    private = next(item for item in report["items"] if item["id"] == "asset:private-dataset")
    assert private["verified_fault_domains"] == ["region-a", "region-b"]
    assert private["required_copies"] == 2


def test_one_copy_is_not_enough_for_non_reconstructable_asset(tmp_path: Path) -> None:
    build_repository(tmp_path)
    archive_path = archive.create_archive(
        "run-1",
        tmp_path,
        copies=[(tmp_path / "copies-a", "region-a")],
    )
    report = archive.verify_archive(archive_path, tmp_path)
    assert report["valid"] is False
    assert any(
        "requires 2 verified independent fault domains" in error for error in report["errors"]
    )


def test_corrupt_local_copy_is_detected(tmp_path: Path) -> None:
    build_repository(tmp_path, include_private_asset=False)
    archive_path = archive.create_archive(
        "run-1",
        tmp_path,
        copies=[(tmp_path / "copies", "local-disk")],
    )
    document = archive.read_json(archive_path)
    copy_path = Path(document["items"][0]["copies"][0]["location"])
    copy_path.write_text("corrupt\n", encoding="utf-8")
    report = archive.verify_archive(archive_path, tmp_path)
    assert report["valid"] is False
    assert any("copy content mismatch" in error for error in report["errors"])


def test_checksum_only_record_is_not_verified(tmp_path: Path) -> None:
    build_repository(tmp_path, include_private_asset=False)
    archive_path = archive.create_archive(
        "run-1",
        tmp_path,
        copies=[(tmp_path / "copies", "local-disk")],
    )
    document = archive.read_json(archive_path)
    document["items"][0]["copies"][0]["method"] = "checksum_only"
    archive.write_json_atomic(archive_path, document)
    with pytest.raises(archive.ArchiveError, match="archive schema"):
        archive.verify_archive(archive_path, tmp_path)


def test_two_external_attestations_can_verify_private_asset(tmp_path: Path) -> None:
    build_repository(tmp_path)
    archive_path = archive.create_archive(
        "run-1",
        tmp_path,
        copies=[(tmp_path / "artifact-copy", "artifact-store")],
        external_copies=[
            (
                "asset:private-dataset",
                "provider-a",
                "https://example.invalid/evidence/a",
                "archive-service-a",
            ),
            (
                "asset:private-dataset",
                "provider-b",
                "https://example.invalid/evidence/b",
                "archive-service-b",
            ),
        ],
    )
    report = archive.verify_archive(archive_path, tmp_path)
    assert report["valid"] is True


def test_retirement_preflight_never_deletes_and_blocks_run_mismatch(tmp_path: Path) -> None:
    build_repository(tmp_path, include_private_asset=False)
    archive_path = archive.create_archive(
        "run-1",
        tmp_path,
        copies=[(tmp_path / "copies", "local-disk")],
    )
    report = archive.retirement_preflight(archive_path, "run", "different-run", tmp_path)
    assert report["decision"] == "blocked"
    assert report["destructive_action_performed"] is False
    assert report["next_action_requires_explicit_authorization"] is True
    assert any("does not match archive run" in blocker for blocker in report["blockers"])


def test_dirty_worktree_blocks_retirement(tmp_path: Path) -> None:
    build_repository(tmp_path, include_private_asset=False)
    archive_path = archive.create_archive(
        "run-1",
        tmp_path,
        copies=[(tmp_path / "copies", "local-disk")],
    )
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    subprocess.run(["git", "init"], cwd=worktree, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"],
        cwd=worktree,
        check=True,
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=worktree, check=True)
    tracked = worktree / "tracked.txt"
    tracked.write_text("tracked\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=worktree, check=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"], cwd=worktree, check=True, capture_output=True
    )
    (worktree / "untracked.txt").write_text("unique\n", encoding="utf-8")

    report = archive.retirement_preflight(
        archive_path,
        "worktree",
        str(worktree),
        tmp_path,
    )
    assert report["decision"] == "blocked"
    assert "worktree contains uncommitted or untracked files" in report["blockers"]
