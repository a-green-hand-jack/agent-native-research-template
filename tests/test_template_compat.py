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
    assert compat.migrate(tmp_path, 4) == []
    assert (tmp_path / "PROJECT.yaml").read_text(encoding="utf-8") == before


def test_version_2_migration_adds_smoke_input_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    initialized_project(tmp_path)
    monkeypatch.setattr(compat.initialize_project, "TEMPLATE_VERSION", 2)
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


def test_version_3_migration_installs_configured_control_surface(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    initialized_project(tmp_path)
    monkeypatch.setattr(compat.initialize_project, "TEMPLATE_VERSION", 3)
    state = compat.initialize_project.load_yaml(tmp_path / "PROJECT.yaml")
    state["template"]["version"] = 2
    state["template"]["applied_migrations"] = [2]
    state.pop("cli_name")
    compat.initialize_project.write_text(
        tmp_path / "PROJECT.yaml", compat.initialize_project.dump_yaml(state)
    )
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "causal-agent-lab"\nversion = "0.1.0"\n'
        'description = "Causal Agent Lab"\ndependencies = []\n\n'
        "[dependency-groups]\ndev = [\n"
        '    "jsonschema>=4.23",\n    "pyyaml>=6.0",\n    "pytest>=8.0",\n]\n\n'
        '[tool.hatch.build.targets.wheel]\npackages = ["src/causal_agent_lab"]\n',
        encoding="utf-8",
    )
    (tmp_path / "Makefile").write_text(
        ".PHONY: research-validate research-run verify\n"
        "research-validate:\n\tuv run python tools/research.py validate\n"
        "\tuv run python tools/evidence.py validate\n"
        "research-run:\n\tuv run python tools/evidence.py run experiments/specs/smoke.yaml\n"
        "verify: research-validate\n",
        encoding="utf-8",
    )
    changes = compat.migrate(tmp_path, 3)
    assert changes == ["write pyproject.toml", "write Makefile", "write README.md"]
    migrated = compat.initialize_project.load_yaml(tmp_path / "PROJECT.yaml")
    assert migrated["cli_name"] == "causal-agent-lab"
    assert migrated["template"]["version"] == 3
    assert migrated["template"]["applied_migrations"] == [2, 3]
    pyproject = (tmp_path / "pyproject.toml").read_text(encoding="utf-8")
    assert 'causal-agent-lab = "tools.control_cli:main"' in pyproject
    assert 'packages = ["src/causal_agent_lab", "tools"]' in pyproject
    assert '"jsonschema>=4.23"' in pyproject.split("[dependency-groups]", 1)[0]
    makefile = (tmp_path / "Makefile").read_text(encoding="utf-8")
    assert "uv run causal-agent-lab experiment validate" in makefile
    assert "control-cli:" in makefile


def test_check_reports_missing_future_migration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    initialized_project(tmp_path)
    monkeypatch.setattr(compat.initialize_project, "TEMPLATE_VERSION", 5)
    assert compat.compatibility_errors(tmp_path) == [
        "project template version 4 requires migration to 5"
    ]
    with pytest.raises(compat.TemplateCompatibilityError, match="missing migration"):
        compat.migrate(tmp_path, 5)


def test_migrations_are_forward_only(tmp_path: Path) -> None:
    initialized_project(tmp_path)
    state = compat.initialize_project.load_yaml(tmp_path / "PROJECT.yaml")
    state["template"]["version"] = 5
    compat.initialize_project.write_text(
        tmp_path / "PROJECT.yaml",
        compat.initialize_project.dump_yaml(state),
    )
    with pytest.raises(compat.TemplateCompatibilityError, match="newer than supported"):
        compat.migrate(tmp_path, 4)


def test_uninitialized_template_cannot_run_downstream_migrations(tmp_path: Path) -> None:
    build_template(tmp_path)
    with pytest.raises(compat.TemplateCompatibilityError, match="initialize the project"):
        compat.migrate(tmp_path, 4)
