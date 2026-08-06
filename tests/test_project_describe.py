from __future__ import annotations

import json
from pathlib import Path

import yaml

from tools import control_cli, describe


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


def test_description_exposes_cli_and_agent_context(tmp_path: Path) -> None:
    write_state(tmp_path)
    description = describe.describe_project(tmp_path)
    assert description["project"]["cli"] == "example"
    assert description["agent_context"]["manifest"] == ".agents/system/manifest.yaml"
    assert "template" not in description["command_groups"]


def test_template_lifecycle_module_is_discoverable(tmp_path: Path) -> None:
    write_state(tmp_path, initialized=False)
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools/template_lifecycle.py").write_text("", encoding="utf-8")
    assert "template" in describe.describe_project(tmp_path)["command_groups"]


def test_control_cli_renders_machine_readable_description(tmp_path: Path, capsys) -> None:
    write_state(tmp_path)
    assert control_cli.main(["project", "describe", "--json"], tmp_path) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["project"]["name"] == "Example Project"
    assert payload["command_groups"][0] == "project"
