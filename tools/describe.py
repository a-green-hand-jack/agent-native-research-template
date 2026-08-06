from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

STATE_PATH = "PROJECT.yaml"


class ProjectDescriptionError(ValueError):
    """Raised when the project descriptor cannot be read safely."""


def load_state(root: Path) -> dict[str, Any]:
    path = root / STATE_PATH
    try:
        state = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ProjectDescriptionError(f"cannot read {path}: {exc}") from exc
    if not isinstance(state, dict):
        raise ProjectDescriptionError(f"{path} must contain a YAML mapping")
    return state


def describe_project(root: Path) -> dict[str, Any]:
    state = load_state(root)
    required = ("project_name", "distribution_name", "package_name", "cli_name", "initialized")
    missing = [key for key in required if key not in state]
    if missing:
        raise ProjectDescriptionError(
            f"{STATE_PATH} is missing required description fields: {', '.join(missing)}"
        )
    command_groups = ["project", "experiment", "workload", "archive", "release"]
    if (root / "tools/template_lifecycle.py").is_file():
        command_groups.insert(1, "template")
    return {
        "schema_version": 1,
        "project": {
            "name": state["project_name"],
            "distribution": state["distribution_name"],
            "package": state["package_name"],
            "cli": state["cli_name"],
            "initialized": state["initialized"],
        },
        "contribution_id": state.get("contribution_id"),
        "command_groups": command_groups,
        "template_provenance": state.get("template"),
    }


def main(argv: list[str] | None = None, root: Path | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Describe project capabilities for humans or agents."
    )
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)
    project_root = (root or Path.cwd()).resolve()
    try:
        description = describe_project(project_root)
        if args.as_json:
            print(json.dumps(description, indent=2, sort_keys=True))
        else:
            project = description["project"]
            print(f"{project['name']} ({project['cli']})")
            print("command groups: " + ", ".join(description["command_groups"]))
        return 0
    except (OSError, ProjectDescriptionError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2
