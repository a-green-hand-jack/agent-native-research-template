from __future__ import annotations

import shutil
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from tools import template_lifecycle


def git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments], cwd=root, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def initialize_git(root: Path) -> None:
    git(root, "init", "-b", "main")
    git(root, "config", "user.email", "test@example.invalid")
    git(root, "config", "user.name", "Test")


def commit_all(root: Path, message: str) -> str:
    git(root, "add", ".")
    git(root, "commit", "-m", message)
    return git(root, "rev-parse", "HEAD")


def build_repositories(tmp_path: Path) -> tuple[Path, Path, str, str]:
    template = tmp_path / "template"
    downstream = tmp_path / "downstream"
    template.mkdir()
    downstream.mkdir()
    initialize_git(template)
    (template / "schemas").mkdir()
    shutil.copy2(
        template_lifecycle.ROOT / template_lifecycle.PLAN_SCHEMA,
        template / template_lifecycle.PLAN_SCHEMA,
    )
    (template / "tracked.txt").write_text("baseline\n", encoding="utf-8")
    baseline = commit_all(template, "baseline")
    (template / "tracked.txt").write_text("target\n", encoding="utf-8")
    (template / "added.txt").write_text("added\n", encoding="utf-8")
    target = commit_all(template, "target")

    initialize_git(downstream)
    (downstream / "tracked.txt").write_text("baseline\n", encoding="utf-8")
    (downstream / "schemas").mkdir()
    shutil.copy2(
        template_lifecycle.ROOT / template_lifecycle.PLAN_SCHEMA,
        downstream / template_lifecycle.PLAN_SCHEMA,
    )
    project = {
        "schema_version": 1,
        "initialized": True,
        "project_name": "Downstream",
        "distribution_name": "downstream",
        "package_name": "downstream",
        "cli_name": "downstream",
        "contribution_id": "downstream",
        "template": {
            "name": "agent-native-research-template",
            "version": 6,
            "initialized_from_commit": baseline,
            "reviewed_template_commit": baseline,
            "applied_migrations": [],
        },
    }
    (downstream / "PROJECT.yaml").write_text(
        yaml.safe_dump(project, sort_keys=False), encoding="utf-8"
    )
    commit_all(downstream, "downstream baseline")
    git(downstream, "switch", "-c", "chore/template-update")
    return template, downstream, baseline, target


def test_update_plan_is_deterministic_and_classifies_safe_changes(tmp_path: Path) -> None:
    template, downstream, baseline, target = build_repositories(tmp_path)
    first = template_lifecycle.create_plan(downstream, template, target)
    second = template_lifecycle.create_plan(downstream, template, target)
    assert first == second
    assert first["mode"] == "update"
    assert first["template"]["baseline_commit"] == baseline
    assert {entry["path"]: entry["disposition"] for entry in first["changes"]} == {
        "added.txt": "safe",
        "tracked.txt": "safe",
    }


def test_apply_and_record_baseline_require_exact_plan_hash(tmp_path: Path) -> None:
    template, downstream, _, target = build_repositories(tmp_path)
    plan = template_lifecycle.create_plan(downstream, template, target)
    changes = template_lifecycle.apply_plan(plan, downstream, template, plan["plan_sha256"])
    assert changes == ["write added.txt", "write tracked.txt"]
    template_lifecycle.record_baseline(plan, downstream, template, plan["plan_sha256"])
    state = yaml.safe_load((downstream / "PROJECT.yaml").read_text(encoding="utf-8"))
    assert state["template"]["reviewed_template_commit"] == target


def test_plan_marks_downstream_customization_as_conflict(tmp_path: Path) -> None:
    template, downstream, _, target = build_repositories(tmp_path)
    (downstream / "tracked.txt").write_text("custom\n", encoding="utf-8")
    plan = template_lifecycle.create_plan(downstream, template, target)
    tracked = next(entry for entry in plan["changes"] if entry["path"] == "tracked.txt")
    assert tracked["ownership"] == "shared/customized"
    assert tracked["disposition"] == "conflict"


def test_adoption_plan_never_classifies_missing_files_as_safe(tmp_path: Path) -> None:
    template, downstream, _, target = build_repositories(tmp_path)
    state = yaml.safe_load((downstream / "PROJECT.yaml").read_text(encoding="utf-8"))
    state["initialized"] = False
    state["template"]["reviewed_template_commit"] = None
    (downstream / "PROJECT.yaml").write_text(
        yaml.safe_dump(state, sort_keys=False), encoding="utf-8"
    )
    plan = template_lifecycle.create_plan(downstream, template, target)
    assert plan["mode"] == "adoption"
    assert all(entry["disposition"] in {"already", "manual"} for entry in plan["changes"])


def test_adoption_plan_does_not_require_project_metadata_or_local_schema(tmp_path: Path) -> None:
    template, downstream, _, target = build_repositories(tmp_path)
    (downstream / "PROJECT.yaml").unlink()
    shutil.rmtree(downstream / "schemas")
    git(downstream, "add", "-A")
    git(downstream, "commit", "-m", "mature repository without template metadata")
    plan = template_lifecycle.create_plan(downstream, template, target)
    assert plan["mode"] == "adoption"
    assert plan["template"]["baseline_commit"] is None


def test_plan_validation_rejects_repository_escape_even_with_matching_hash(tmp_path: Path) -> None:
    template, downstream, _, target = build_repositories(tmp_path)
    plan = template_lifecycle.create_plan(downstream, template, target)
    malicious = deepcopy(plan)
    malicious["changes"][0]["path"] = "../escape.txt"
    payload = {key: value for key, value in malicious.items() if key != "plan_sha256"}
    malicious["plan_sha256"] = template_lifecycle.canonical_sha256(payload)
    with pytest.raises(template_lifecycle.TemplateLifecycleError, match="repository-relative"):
        template_lifecycle.validate_plan(malicious, template)


def test_plan_rejects_downstream_parent_symlink_escape(tmp_path: Path) -> None:
    template, downstream, _, target = build_repositories(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (template / "linked").mkdir()
    (template / "linked/payload.txt").write_text("target\n", encoding="utf-8")
    target = commit_all(template, "add nested target")
    (downstream / "linked").symlink_to(outside, target_is_directory=True)
    with pytest.raises(template_lifecycle.TemplateLifecycleError, match="symbolic link"):
        template_lifecycle.create_plan(downstream, template, target)
    assert not (outside / "payload.txt").exists()


def test_changed_paths_preserves_tabs_and_newlines_in_file_names(tmp_path: Path) -> None:
    template = tmp_path / "template"
    template.mkdir()
    initialize_git(template)
    (template / "base.txt").write_text("base\n", encoding="utf-8")
    baseline = commit_all(template, "baseline")
    names = ["tab\tname.txt", "line\nbreak.txt"]
    for name in names:
        (template / name).write_text("content\n", encoding="utf-8")
    target = commit_all(template, "unusual names")
    assert template_lifecycle.changed_paths(template, baseline, target) == [
        ("A", name) for name in sorted(names)
    ]
