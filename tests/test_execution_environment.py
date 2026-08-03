from __future__ import annotations

from pathlib import Path

import pytest

from tools import execution_environment


def profile() -> dict[str, object]:
    return {
        "environment": {"OUTPUT_ROOT": "${PROJECT_ROOT}/outputs"},
        "inherit_environment": ["PATH"],
    }


def test_only_declared_environment_reaches_execution(tmp_path: Path) -> None:
    environment, evidence = execution_environment.resolve_environment(
        profile(), tmp_path, 7, {"PATH": "/bin", "UNDECLARED": "hidden"}
    )
    assert environment == {
        "OUTPUT_ROOT": f"{tmp_path.resolve()}/outputs",
        "PATH": "/bin",
        "RESEARCH_SEED": "7",
    }
    assert "UNDECLARED" not in environment
    assert evidence["inherited"][0]["name"] == "PATH"
    assert "value" not in evidence["inherited"][0]


def test_missing_inherited_variable_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(execution_environment.ExecutionEnvironmentError, match="required inherited"):
        execution_environment.resolve_environment(profile(), tmp_path, 0, {})


def test_secret_like_names_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(execution_environment.ExecutionEnvironmentError, match="secret-bearing"):
        execution_environment.declared_environment(
            {"environment": {"API_TOKEN": "not-a-secret"}}, tmp_path
        )


def test_undeclared_placeholder_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(execution_environment.ExecutionEnvironmentError, match="undeclared"):
        execution_environment.declared_environment(
            {"environment": {"OUTPUT": "${HOME}/outputs"}}, tmp_path
        )
