from __future__ import annotations

import sys
from pathlib import Path

import yaml

from . import archive, evidence

DEFAULT_CLI_NAME = "researchctl"
PROJECT_FILE = "PROJECT.yaml"


class ControlCLIError(ValueError):
    """Raised when the project control surface cannot resolve its repository."""


def find_project_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    candidates = (current, *current.parents)
    for candidate in candidates:
        if (candidate / PROJECT_FILE).is_file():
            return candidate
    raise ControlCLIError(
        f"cannot find {PROJECT_FILE} from {current}; run the command inside an initialized project"
    )


def configured_cli_name(root: Path) -> str:
    try:
        project = yaml.safe_load((root / PROJECT_FILE).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ControlCLIError(f"cannot read {PROJECT_FILE}: {exc}") from exc
    if not isinstance(project, dict):
        raise ControlCLIError(f"{PROJECT_FILE} must contain a YAML mapping")
    value = project.get("cli_name", DEFAULT_CLI_NAME)
    if not isinstance(value, str) or not value.strip():
        raise ControlCLIError("PROJECT.yaml cli_name must be a non-empty string")
    return value


def render_help(root: Path) -> str:
    name = configured_cli_name(root)
    return (
        f"usage: {name} <group> <command> [arguments]\n\n"
        "Project-local research control plane.\n\n"
        "groups:\n"
        "  experiment   validate, plan, preflight, run, recover, inspect, verify, and promote\n"
        "  archive      create verified copies and produce retirement decisions\n\n"
        f"Run '{name} experiment --help' or '{name} archive --help' for group commands.\n"
    )


def main(argv: list[str] | None = None, root: Path | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    try:
        project_root = root.resolve() if root is not None else find_project_root()
        if not arguments or arguments[0] in {"-h", "--help"}:
            print(render_help(project_root), end="")
            return 0
        group, *group_arguments = arguments
        if group == "experiment":
            return evidence.main(group_arguments, project_root)
        if group == "archive":
            return archive.main(group_arguments, project_root)
        raise ControlCLIError(
            f"unknown command group {group!r}; expected 'experiment' or 'archive'"
        )
    except ControlCLIError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
