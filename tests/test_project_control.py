from __future__ import annotations

from pathlib import Path

from repo_cli import project
from tools import project as legacy_project


def test_checked_repository_matches_project_identity_and_projection() -> None:
    root = Path(__file__).resolve().parents[1]
    assert project.check_project(root) == []


def test_project_check_command_uses_repo_cli_implementation() -> None:
    root = Path(__file__).resolve().parents[1]
    assert project.main(["check"], root) == 0


def test_legacy_project_module_is_a_compatibility_adapter() -> None:
    assert legacy_project.check_project is project.check_project
    assert legacy_project.ProjectIdentity is project.ProjectIdentity
