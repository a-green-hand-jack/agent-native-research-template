from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from tools import control_cli


def write_project(root: Path, cli_name: str = "researchctl") -> None:
    (root / "PROJECT.yaml").write_text(
        f"schema_version: 1\ninitialized: false\ncli_name: {cli_name}\n",
        encoding="utf-8",
    )


def test_find_project_root_walks_upward(tmp_path: Path) -> None:
    write_project(tmp_path)
    nested = tmp_path / "a/b/c"
    nested.mkdir(parents=True)
    assert control_cli.find_project_root(nested) == tmp_path


def test_help_uses_configured_project_command(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_project(tmp_path, "labctl")
    assert control_cli.main(["--help"], tmp_path) == 0
    output = capsys.readouterr().out
    assert "usage: labctl" in output
    assert "labctl experiment --help" in output


def test_experiment_group_delegates_to_canonical_runner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_project(tmp_path)
    observed: dict[str, object] = {}

    def fake_main(argv: list[str], root: Path) -> int:
        observed.update(argv=argv, root=root)
        return 17

    monkeypatch.setattr(control_cli.evidence, "main", fake_main)
    assert control_cli.main(["experiment", "plan", "study.yaml"], tmp_path) == 17
    assert observed == {"argv": ["plan", "study.yaml"], "root": tmp_path}


def test_archive_group_delegates_to_canonical_archive_tool(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    write_project(tmp_path)
    observed: dict[str, object] = {}

    def fake_main(argv: list[str], root: Path) -> int:
        observed.update(argv=argv, root=root)
        return 19

    monkeypatch.setattr(control_cli.archive, "main", fake_main)
    assert control_cli.main(["archive", "verify", "archive.json"], tmp_path) == 19
    assert observed == {"argv": ["verify", "archive.json"], "root": tmp_path}


def test_package_installs_one_configured_console_entry() -> None:
    root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    cli_name = control_cli.configured_cli_name(root)
    assert project["project"]["scripts"] == {cli_name: "tools.control_cli:main"}
    assert set(project["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"]) == {
        "src/project",
        "tools",
    }
