from __future__ import annotations

from pathlib import Path

from tools import project


def test_checked_repository_matches_project_identity_and_projection() -> None:
    root = Path(__file__).resolve().parents[1]
    assert project.check_project(root) == []


def test_project_check_command_uses_retained_functional_module() -> None:
    root = Path(__file__).resolve().parents[1]
    assert project.main(["check"], root) == 0
