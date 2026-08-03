from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

SPEC = importlib.util.spec_from_file_location("template_compat_tool", TOOLS / "template_compat.py")
assert SPEC and SPEC.loader
compat = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(compat)

from test_initialize_project import build_template, identity


def initialized_project(root: Path) -> None:
    build_template(root)
    compat.initialize_project.apply_changes(root, identity())


def test_current_initialized_project_is_compatible(tmp_path: Path) -> None:
    initialized_project(tmp_path)
    assert compat.compatibility_errors(tmp_path) == []


def test_migrate_to_current_version_is_explicit_noop(tmp_path: Path) -> None:
    initialized_project(tmp_path)
    before = (tmp_path / "PROJECT.yaml").read_text(encoding="utf-8")
    assert compat.migrate(tmp_path, 2) == []
    assert (tmp_path / "PROJECT.yaml").read_text(encoding="utf-8") == before


def test_version_2_migration_adds_smoke_input_identity(tmp_path: Path) -> None:
    initialized_project(tmp_path)
    state = compat.initialize_project.load_yaml(tmp_path / "PROJECT.yaml")
    state["template"]["version"] = 1
    state["template"]["applied_migrations"] = []
    compat.initialize_project.write_text(
        tmp_path / "PROJECT.yaml",
        compat.initialize_project.dump_yaml(state),
    )
    smoke = tmp_path / "experiments/specs/smoke.yaml"
    specification = compat.initialize_project.load_yaml(smoke)
    specification.pop("inputs", None)
    compat.initialize_project.write_text(
        smoke,
        compat.initialize_project.dump_yaml(specification),
    )

    assert compat.compatibility_errors(tmp_path) == [
        "project template version 1 requires migration to 2"
    ]
    assert compat.migrate(tmp_path, 2) == ["write experiments/specs/smoke.yaml"]
    migrated = compat.initialize_project.load_yaml(tmp_path / "PROJECT.yaml")
    assert migrated["template"]["version"] == 2
    assert migrated["template"]["applied_migrations"] == [2]
    assert compat.initialize_project.load_yaml(smoke)["inputs"] == [
        {"id": "smoke-source", "kind": "path", "path": "src"}
    ]
    assert compat.compatibility_errors(tmp_path) == []


def test_check_reports_missing_future_migration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    initialized_project(tmp_path)
    monkeypatch.setattr(compat.initialize_project, "TEMPLATE_VERSION", 3)
    assert compat.compatibility_errors(tmp_path) == [
        "project template version 2 requires migration to 3"
    ]
    with pytest.raises(compat.TemplateCompatibilityError, match="missing migration"):
        compat.migrate(tmp_path, 3)


def test_migrations_are_forward_only(tmp_path: Path) -> None:
    initialized_project(tmp_path)
    state = compat.initialize_project.load_yaml(tmp_path / "PROJECT.yaml")
    state["template"]["version"] = 3
    compat.initialize_project.write_text(
        tmp_path / "PROJECT.yaml",
        compat.initialize_project.dump_yaml(state),
    )
    with pytest.raises(compat.TemplateCompatibilityError, match="newer than supported"):
        compat.migrate(tmp_path, 2)


def test_uninitialized_template_cannot_run_downstream_migrations(tmp_path: Path) -> None:
    build_template(tmp_path)
    with pytest.raises(compat.TemplateCompatibilityError, match="initialize the project"):
        compat.migrate(tmp_path, 2)
