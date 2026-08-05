from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from tools import release


def git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments], cwd=root, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def build_project(root: Path) -> tuple[Path, str]:
    git(root, "init", "-b", "main")
    git(root, "config", "user.email", "test@example.invalid")
    git(root, "config", "user.name", "Test")
    (root / "schemas").mkdir()
    for schema in (release.PROFILE_SCHEMA, release.MANIFEST_SCHEMA):
        shutil.copy2(release.ROOT / schema, root / schema)
    (root / ".gitignore").write_text("dist/\n", encoding="utf-8")
    (root / "payload.txt").write_text("release payload\n", encoding="utf-8")
    profile = root / "RELEASE.yaml"
    profile.write_text(
        "schema_version: 1\n"
        "id: source\n"
        "include:\n- payload.txt\n"
        "verification_commands:\n"
        "- [python, -c, \"from pathlib import Path; assert Path('payload.txt').is_file()\"]\n",
        encoding="utf-8",
    )
    git(root, "add", ".")
    git(root, "commit", "-m", "project")
    return profile, git(root, "rev-parse", "HEAD")


def test_build_creates_verified_draft_that_is_never_release_ready(tmp_path: Path) -> None:
    profile, _ = build_project(tmp_path)
    manifest_path = release.build_release(profile, tmp_path, release_id="release-1")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["release_ready"] is False
    assert manifest["approval"] is None
    assert manifest["verification"]["passed"] is True
    assert release.verify_release(manifest_path, tmp_path)["valid"] is True


def test_verify_detects_changed_artifact(tmp_path: Path) -> None:
    profile, _ = build_project(tmp_path)
    manifest_path = release.build_release(profile, tmp_path, release_id="release-1")
    artifact = manifest_path.parent / "artifact.zip"
    artifact.write_bytes(b"corrupt")
    assert release.verify_release(manifest_path, tmp_path)["valid"] is False


def test_strict_record_requires_clean_exact_revision_and_is_immutable(tmp_path: Path) -> None:
    profile, revision = build_project(tmp_path)
    manifest_path = release.build_release(profile, tmp_path, release_id="release-1")
    approved, provenance = release.record_release(manifest_path, "maintainer", revision, tmp_path)
    document = json.loads(approved.read_text(encoding="utf-8"))
    assert document["release_ready"] is True
    assert document["approval"]["approved_by"] == "maintainer"
    assert "Release ready: `true`" in provenance.read_text(encoding="utf-8")
    with pytest.raises(release.ReleaseError, match="immutable"):
        release.record_release(manifest_path, "maintainer", revision, tmp_path)


def test_strict_record_rejects_dirty_source(tmp_path: Path) -> None:
    profile, revision = build_project(tmp_path)
    manifest_path = release.build_release(profile, tmp_path, release_id="release-1")
    (tmp_path / "payload.txt").write_text("changed\n", encoding="utf-8")
    with pytest.raises(release.ReleaseError, match="not verified"):
        release.record_release(manifest_path, "maintainer", revision, tmp_path)


def test_release_profile_cannot_package_managed_output(tmp_path: Path) -> None:
    profile, _ = build_project(tmp_path)
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist/generated.txt").write_text("generated\n", encoding="utf-8")
    document = release.load_yaml(profile)
    document["include"] = ["dist"]
    profile.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    with pytest.raises(release.ReleaseError, match="managed or governance"):
        release.build_release(profile, tmp_path, release_id="release-1")


def test_verify_reruns_artifact_only_commands_instead_of_trusting_manifest(tmp_path: Path) -> None:
    profile, _ = build_project(tmp_path)
    manifest_path = release.build_release(profile, tmp_path, release_id="release-1")
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    document["verification"]["commands"] = [["python", "-c", "raise SystemExit(9)"]]
    release.archive.write_json_atomic(manifest_path, document)
    report = release.verify_release(manifest_path, tmp_path)
    assert report["valid"] is False
    assert any("commands differ" in error for error in report["errors"])


def test_release_id_cannot_escape_dist_directory(tmp_path: Path) -> None:
    profile, _ = build_project(tmp_path)
    with pytest.raises(release.ReleaseError, match="release ID"):
        release.build_release(profile, tmp_path, release_id="../../escape")


def test_verify_rejects_manifest_and_artifact_path_escape(tmp_path: Path) -> None:
    profile, _ = build_project(tmp_path)
    manifest_path = release.build_release(profile, tmp_path, release_id="release-1")
    outside = tmp_path / "copied-manifest.json"
    shutil.copy2(manifest_path, outside)
    assert release.verify_release(outside, tmp_path)["valid"] is False
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    document["artifact"]["path"] = "payload.txt"
    release.archive.write_json_atomic(manifest_path, document)
    assert release.verify_release(manifest_path, tmp_path)["valid"] is False


def test_strict_record_rejects_dirty_build_after_checkout_is_restored(tmp_path: Path) -> None:
    profile, revision = build_project(tmp_path)
    (tmp_path / "payload.txt").write_text("dirty build\n", encoding="utf-8")
    manifest_path = release.build_release(profile, tmp_path, release_id="release-1")
    git(tmp_path, "restore", "payload.txt")
    with pytest.raises(release.ReleaseError, match="dirty source"):
        release.record_release(manifest_path, "maintainer", revision, tmp_path)


def test_verify_rejects_manifest_fact_or_command_omission(tmp_path: Path) -> None:
    profile, _ = build_project(tmp_path)
    manifest_path = release.build_release(profile, tmp_path, release_id="release-1")
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    document["verification"]["commands"] = [["python", "-V"]]
    release.archive.write_json_atomic(manifest_path, document)
    assert release.verify_release(manifest_path, tmp_path)["valid"] is False


def test_release_rejects_managed_directory_symlinks(tmp_path: Path) -> None:
    profile, _ = build_project(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / "dist").symlink_to(outside, target_is_directory=True)
    with pytest.raises(release.ReleaseError, match="symbolic link"):
        release.build_release(profile, tmp_path, release_id="release-1")
