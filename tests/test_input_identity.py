from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[1] / "tools" / "input_identity.py"
SPEC = importlib.util.spec_from_file_location("input_identity_tool", MODULE)
assert SPEC and SPEC.loader
identity = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(identity)


def test_path_file_and_directory_identities_are_stable(tmp_path: Path) -> None:
    (tmp_path / "inputs").mkdir()
    (tmp_path / "inputs/a.txt").write_text("alpha", encoding="utf-8")
    (tmp_path / "inputs/b.txt").write_text("beta", encoding="utf-8")
    records = identity.resolve_inputs(
        [
            {"id": "single-file", "kind": "path", "path": "inputs/a.txt"},
            {"id": "input-tree", "kind": "path", "path": "inputs"},
        ],
        tmp_path,
    )
    assert records[0]["path_type"] == "file"
    assert records[0]["file_count"] == 1
    assert records[1]["path_type"] == "directory"
    assert records[1]["file_count"] == 2
    assert (
        identity.resolve_inputs(
            [
                {"id": "single-file", "kind": "path", "path": "inputs/a.txt"},
                {"id": "input-tree", "kind": "path", "path": "inputs"},
            ],
            tmp_path,
        )
        == records
    )


def test_path_input_drift_detects_changed_content(tmp_path: Path) -> None:
    path = tmp_path / "input.txt"
    path.write_text("before", encoding="utf-8")
    records = identity.resolve_inputs(
        [{"id": "fixture", "kind": "path", "path": "input.txt"}],
        tmp_path,
    )
    path.write_text("after", encoding="utf-8")
    assert identity.recorded_input_drift(records, tmp_path) == ["input fixture changed: input.txt"]


def test_uri_and_opaque_identities_preserve_declared_versions(tmp_path: Path) -> None:
    digest = "a" * 64
    records = identity.resolve_inputs(
        [
            {
                "id": "release",
                "kind": "uri",
                "uri": "https://example.invalid/releases/1",
                "version": "1",
                "sha256": digest,
            },
            {
                "id": "private-split",
                "kind": "opaque",
                "value": "split-2026-08",
                "version": "4",
            },
        ],
        tmp_path,
    )
    assert records == [
        {
            "id": "release",
            "kind": "uri",
            "uri": "https://example.invalid/releases/1",
            "version": "1",
            "sha256": digest,
        },
        {
            "id": "private-split",
            "kind": "opaque",
            "value": "split-2026-08",
            "version": "4",
        },
    ]
    assert identity.recorded_input_drift(records, tmp_path) == []


def test_duplicate_input_ids_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(identity.InputIdentityError, match="duplicate input ID"):
        identity.resolve_inputs(
            [
                {"id": "same", "kind": "opaque", "value": "one"},
                {"id": "same", "kind": "opaque", "value": "two"},
            ],
            tmp_path,
        )


def test_path_input_rejects_symbolic_links(tmp_path: Path) -> None:
    target = tmp_path / "target.txt"
    target.write_text("data", encoding="utf-8")
    link = tmp_path / "link.txt"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symbolic links are unavailable on this platform")
    with pytest.raises(identity.InputIdentityError, match="symbolic link"):
        identity.resolve_inputs(
            [{"id": "linked", "kind": "path", "path": "link.txt"}],
            tmp_path,
        )
