from __future__ import annotations

import json
from pathlib import Path

import yaml

from repo_cli import cli, describe


def write_state(root: Path, *, initialized: bool = True) -> None:
    (root / "PROJECT.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "initialized": initialized,
                "project_name": "Example Project",
                "distribution_name": "example-project",
                "package_name": "example_project",
                "cli_name": "example",
                "contribution_id": "core",
                "template": {
                    "name": "agent-native-research-template",
                    "version": 7,
                    "initialized_from_commit": "abc",
                    "reviewed_template_commit": "abc",
                    "applied_migrations": [],
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_description_exposes_separate_repo_and_project_clis(tmp_path: Path) -> None:
    write_state(tmp_path)
    description = describe.describe_repository(tmp_path)
    assert description["repository"] == {
        "cli": "repoctl",
        "commands": ["describe", "check"],
    }
    assert description["project"]["cli"] == "example"
    assert "template" not in description["project"]["command_groups"]


def test_template_lifecycle_module_is_discoverable(tmp_path: Path) -> None:
    write_state(tmp_path, initialized=False)
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools/template_lifecycle.py").write_text("", encoding="utf-8")
    assert "template" in describe.describe_repository(tmp_path)["project"]["command_groups"]


def test_repo_cli_renders_machine_readable_description(tmp_path: Path, capsys) -> None:
    write_state(tmp_path)
    assert cli.main(["describe", "--json"], tmp_path) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["project"]["name"] == "Example Project"
    assert payload["repository"]["cli"] == "repoctl"


def test_repo_description_does_not_depend_on_agent_sidecar(tmp_path: Path) -> None:
    write_state(tmp_path)
    payload = json.dumps(describe.describe_repository(tmp_path))
    assert ".agents" not in payload
