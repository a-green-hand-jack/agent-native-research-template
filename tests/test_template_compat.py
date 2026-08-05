from __future__ import annotations

from pathlib import Path

import pytest

from tools import template_compat as compat


def write_files(root: Path, files: dict[str, str]) -> None:
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def initialized_project(root: Path) -> None:
    write_files(
        root,
        {
            "PROJECT.yaml": (
                "schema_version: 1\ninitialized: true\nproject_name: Causal Agent Lab\n"
                "distribution_name: causal-agent-lab\npackage_name: causal_agent_lab\n"
                "cli_name: causal-lab\ncontribution_id: causal-policy\n"
                "template:\n  name: agent-native-research-template\n  version: 6\n"
                "  initialized_from_commit: unknown\n  reviewed_template_commit: unknown\n"
                "  applied_migrations: []\n"
            ),
            "pyproject.toml": (
                '[project]\nname = "causal-agent-lab"\nversion = "0.1.0"\n'
                'description = "Causal Agent Lab"\ndependencies = []\n\n'
                '[project.scripts]\ncausal-lab = "tools.control_cli:main"\n\n'
                '[tool.hatch.build.targets.wheel]\npackages = ["src/causal_agent_lab", "tools"]\n'
            ),
            "experiments/specs/smoke.yaml": (
                "contribution: causal-policy\n"
                "inputs:\n  - id: smoke-source\n    kind: path\n    path: src\n"
            ),
            "README.md": "# Causal Agent Lab\n",
            "Makefile": "verify:\n\tuv run causal-lab experiment validate\n",
        },
    )


def uninitialized_template(root: Path) -> None:
    write_files(
        root,
        {
            "PROJECT.yaml": (
                "schema_version: 1\ninitialized: false\n"
                "project_name: Agent-Native Research Template\n"
                "distribution_name: agent-native-project\npackage_name: project\n"
                "cli_name: researchctl\ncontribution_id: bootstrap\n"
                "template:\n  name: agent-native-research-template\n  version: 6\n"
                "  initialized_from_commit: null\n  reviewed_template_commit: null\n"
                "  applied_migrations: []\n"
            )
        },
    )


def test_current_initialized_project_is_compatible(tmp_path: Path) -> None:
    initialized_project(tmp_path)
    assert compat.compatibility_errors(tmp_path) == []


def test_migrate_to_current_version_is_explicit_noop(tmp_path: Path) -> None:
    initialized_project(tmp_path)
    before = (tmp_path / "PROJECT.yaml").read_text(encoding="utf-8")
    assert compat.migrate(tmp_path, 6) == []
    assert (tmp_path / "PROJECT.yaml").read_text(encoding="utf-8") == before


def test_version_2_migration_adds_smoke_input_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    initialized_project(tmp_path)
    monkeypatch.setattr(compat.project, "TEMPLATE_VERSION", 2)
    state = compat.project.load_yaml(tmp_path / "PROJECT.yaml")
    state["template"]["version"] = 1
    state["template"]["applied_migrations"] = []
    compat.project.write_text(
        tmp_path / "PROJECT.yaml",
        compat.project.dump_yaml(state),
    )
    smoke = tmp_path / "experiments/specs/smoke.yaml"
    specification = compat.project.load_yaml(smoke)
    specification.pop("inputs", None)
    compat.project.write_text(
        smoke,
        compat.project.dump_yaml(specification),
    )

    assert compat.compatibility_errors(tmp_path) == [
        "project template version 1 requires migration to 2"
    ]
    assert compat.migrate(tmp_path, 2) == ["write experiments/specs/smoke.yaml"]
    migrated = compat.project.load_yaml(tmp_path / "PROJECT.yaml")
    assert migrated["template"]["version"] == 2
    assert migrated["template"]["applied_migrations"] == [2]
    assert compat.project.load_yaml(smoke)["inputs"] == [
        {"id": "smoke-source", "kind": "path", "path": "src"}
    ]
    assert compat.compatibility_errors(tmp_path) == []


def test_version_3_migration_installs_configured_control_surface(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    initialized_project(tmp_path)
    monkeypatch.setattr(compat.project, "TEMPLATE_VERSION", 3)
    state = compat.project.load_yaml(tmp_path / "PROJECT.yaml")
    state["template"]["version"] = 2
    state["template"]["applied_migrations"] = [2]
    state.pop("cli_name")
    compat.project.write_text(tmp_path / "PROJECT.yaml", compat.project.dump_yaml(state))
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
    migrated = compat.project.load_yaml(tmp_path / "PROJECT.yaml")
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


def test_version_6_migration_records_reviewed_template_baseline(
    tmp_path: Path,
) -> None:
    initialized_project(tmp_path)
    state = compat.project.load_yaml(tmp_path / "PROJECT.yaml")
    state["template"]["version"] = 5
    state["template"].pop("reviewed_template_commit")
    compat.project.write_text(tmp_path / "PROJECT.yaml", compat.project.dump_yaml(state))
    assert compat.compatibility_errors(tmp_path) == [
        "project template version 5 requires migration to 6"
    ]
    assert compat.migrate(tmp_path, 6) == []
    migrated = compat.project.load_yaml(tmp_path / "PROJECT.yaml")
    assert migrated["template"]["reviewed_template_commit"] == "unknown"
    assert migrated["template"]["applied_migrations"] == [6]


def test_version_6_migration_replaces_explicit_null_baseline(tmp_path: Path) -> None:
    initialized_project(tmp_path)
    state = compat.project.load_yaml(tmp_path / "PROJECT.yaml")
    state["template"]["version"] = 5
    state["template"]["reviewed_template_commit"] = None
    compat.project.write_text(tmp_path / "PROJECT.yaml", compat.project.dump_yaml(state))
    assert compat.migrate(tmp_path, 6) == []
    migrated = compat.project.load_yaml(tmp_path / "PROJECT.yaml")
    assert migrated["template"]["reviewed_template_commit"] == "unknown"
    assert compat.compatibility_errors(tmp_path) == []


def test_migrations_are_forward_only(tmp_path: Path) -> None:
    initialized_project(tmp_path)
    state = compat.project.load_yaml(tmp_path / "PROJECT.yaml")
    state["template"]["version"] = 7
    compat.project.write_text(
        tmp_path / "PROJECT.yaml",
        compat.project.dump_yaml(state),
    )
    with pytest.raises(compat.TemplateCompatibilityError, match="newer than supported"):
        compat.migrate(tmp_path, 6)


def test_uninitialized_template_cannot_run_downstream_migrations(tmp_path: Path) -> None:
    uninitialized_template(tmp_path)
    with pytest.raises(compat.TemplateCompatibilityError, match="initialize the project"):
        compat.migrate(tmp_path, 4)
