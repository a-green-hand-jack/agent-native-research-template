from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parents[1] / "tools" / "initialize_project.py"
SPEC = importlib.util.spec_from_file_location("initializer", MODULE)
assert SPEC and SPEC.loader
initializer = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = initializer
SPEC.loader.exec_module(initializer)


def build_template(root: Path) -> None:
    files = {
        "PROJECT.yaml": (
            "schema_version: 1\ninitialized: false\n"
            "project_name: Agent-Native Research Template\n"
            "distribution_name: agent-native-project\n"
            "package_name: project\ncli_name: researchctl\ncontribution_id: bootstrap\n"
            "template:\n"
            "  name: agent-native-research-template\n"
            "  version: 3\n"
            "  initialized_from_commit: null\n"
            "  applied_migrations: []\n"
        ),
        "pyproject.toml": (
            '[project]\nname = "agent-native-project"\nversion = "0.1.0"\n'
            'description = "Bootstrap package for an agent-native research project"\n'
            '[project.scripts]\nresearchctl = "tools.control_cli:main"\n'
            '[tool.hatch.build.targets.wheel]\npackages = ["src/project", "tools"]\n'
        ),
        "uv.lock": '[[package]]\nname = "agent-native-project"\n',
        "Makefile": (
            ".PHONY: research-validate research-run verify\n"
            "research-validate:\n\tuv run researchctl experiment validate\n"
            "research-run:\n\tuv run researchctl experiment run experiments/specs/smoke.yaml\n"
            "verify: research-validate\n"
        ),
        "CONTRIBUTIONS.md": (
            "| ID | Contribution | Code | Parameters | Evidence | Status |\n"
            "|---|---|---|---|---|---|\n"
            "| bootstrap | Replace with the first real contribution | `src/project/` | "
            "`configs/base.yaml` | `evals/smoke.yaml` | bootstrap |\n"
        ),
        "experiments/specs/smoke.yaml": "contribution: bootstrap\n",
        "src/project/__init__.py": (
            '"""Bootstrap package. Replace this module with the first real project slice."""\n\n'
            "def template_status() -> str:\n"
            '    """Return a stable value used by the bootstrap smoke test."""\n'
            '    return "ready"\n'
        ),
        "tests/smoke/test_template.py": (
            "from project import template_status\n\n"
            "def test_template_vertical_slice() -> None:\n"
            '    assert template_status() == "ready"\n'
        ),
        "README.md": "# Agent-Native Research Template\n\nTemplate description.\n",
    }
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def identity() -> object:
    return initializer.ProjectIdentity(
        project_name="Causal Agent Lab",
        distribution_name="causal-agent-lab",
        package_name="causal_agent_lab",
        cli_name="causal-lab",
        contribution_id="causal-policy",
    )


def test_uninitialized_template_check_passes(tmp_path: Path) -> None:
    build_template(tmp_path)
    assert initializer.check_project(tmp_path) == []


def test_dry_run_does_not_change_files(tmp_path: Path) -> None:
    build_template(tmp_path)
    before = (tmp_path / "pyproject.toml").read_text(encoding="utf-8")
    planned = initializer.apply_changes(tmp_path, identity(), dry_run=True)
    assert any("src/causal_agent_lab/__init__.py" in item for item in planned)
    assert (tmp_path / "pyproject.toml").read_text(encoding="utf-8") == before
    assert not (tmp_path / "src/causal_agent_lab").exists()


def test_apply_updates_identity_and_records_template_provenance(tmp_path: Path) -> None:
    build_template(tmp_path)
    initializer.apply_changes(tmp_path, identity())
    assert initializer.check_project(tmp_path) == []
    assert (tmp_path / "src/causal_agent_lab/__init__.py").is_file()
    assert (tmp_path / "tests/smoke/test_project.py").is_file()
    assert not (tmp_path / "src/project").exists()
    assert not (tmp_path / "tests/smoke/test_template.py").exists()
    state = initializer.load_yaml(tmp_path / "PROJECT.yaml")
    assert state["initialized"] is True
    assert state["package_name"] == "causal_agent_lab"
    assert state["cli_name"] == "causal-lab"
    assert 'causal-lab = "tools.control_cli:main"' in (tmp_path / "pyproject.toml").read_text(
        encoding="utf-8"
    )
    assert state["template"] == {
        "name": "agent-native-research-template",
        "version": 3,
        "initialized_from_commit": "unknown",
        "applied_migrations": [],
    }
    readme = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "Initialized from Agent-Native Research Template v3 at `unknown`" in readme


def test_check_rejects_invalid_template_metadata(tmp_path: Path) -> None:
    build_template(tmp_path)
    project = tmp_path / "PROJECT.yaml"
    project.write_text(
        project.read_text(encoding="utf-8").replace("version: 3", "version: 4"),
        encoding="utf-8",
    )
    assert any("newer than supported" in error for error in initializer.check_project(tmp_path))


def test_check_detects_residue_after_initialization(tmp_path: Path) -> None:
    build_template(tmp_path)
    initializer.apply_changes(tmp_path, identity())
    with (tmp_path / "pyproject.toml").open("a", encoding="utf-8") as handle:
        handle.write("# agent-native-project\n")
    assert any("template residue" in error for error in initializer.check_project(tmp_path))


def test_invalid_identity_is_rejected(tmp_path: Path) -> None:
    build_template(tmp_path)
    invalid = initializer.ProjectIdentity(
        project_name="Bad",
        distribution_name="Bad Name",
        package_name="bad-name",
        cli_name="Bad CLI",
        contribution_id="bootstrap",
    )
    with pytest.raises(initializer.InitializationError):
        initializer.apply_changes(tmp_path, invalid)


def test_apply_is_functional_only(tmp_path: Path) -> None:
    build_template(tmp_path)
    initializer.apply_changes(tmp_path, identity())
    assert initializer.check_project(tmp_path) == []
