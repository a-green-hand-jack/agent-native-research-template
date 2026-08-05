from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = "PROJECT.yaml"
TEMPLATE_NAME = "agent-native-research-template"
TEMPLATE_VERSION = 7
TEMPLATE_STATE = {
    "project_name": "Agent-Native Research Template",
    "distribution_name": "agent-native-project",
    "package_name": "project",
    "cli_name": "researchctl",
    "contribution_id": "bootstrap",
}
DISTRIBUTION_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PACKAGE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
CONTRIBUTION_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
CLI_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class ProjectCheckError(ValueError):
    """Raised when project identity or provenance cannot be read safely."""


@dataclass(frozen=True)
class ProjectIdentity:
    project_name: str
    distribution_name: str
    package_name: str
    cli_name: str
    contribution_id: str


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ProjectCheckError(f"cannot read {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ProjectCheckError(f"{path} must contain a YAML mapping")
    return data


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def dump_yaml(data: dict[str, Any]) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


def validate_identity(identity: ProjectIdentity) -> None:
    if not identity.project_name.strip():
        raise ProjectCheckError("project name must not be empty")
    if not DISTRIBUTION_PATTERN.fullmatch(identity.distribution_name):
        raise ProjectCheckError(
            "distribution name must use lowercase letters, digits, and single hyphens"
        )
    if not PACKAGE_PATTERN.fullmatch(identity.package_name):
        raise ProjectCheckError("package name must be a lowercase Python identifier")
    if not CLI_PATTERN.fullmatch(identity.cli_name):
        raise ProjectCheckError("CLI name must use lowercase letters, digits, and single hyphens")
    if not CONTRIBUTION_PATTERN.fullmatch(identity.contribution_id):
        raise ProjectCheckError("contribution ID must be a stable lowercase identifier")
    if identity.distribution_name == TEMPLATE_STATE["distribution_name"]:
        raise ProjectCheckError("distribution name must replace the template value")
    if identity.package_name == TEMPLATE_STATE["package_name"]:
        raise ProjectCheckError("package name must replace the template value")
    if identity.cli_name == TEMPLATE_STATE["cli_name"]:
        raise ProjectCheckError("CLI name must replace the template value")
    if identity.contribution_id == TEMPLATE_STATE["contribution_id"]:
        raise ProjectCheckError("contribution ID must replace the template value")


def template_metadata_errors(state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    metadata = state.get("template")
    if not isinstance(metadata, dict):
        return ["PROJECT.yaml template must be a mapping"]
    if metadata.get("name") != TEMPLATE_NAME:
        errors.append(f"PROJECT.yaml template.name must be {TEMPLATE_NAME!r}")
    version = metadata.get("version")
    if not isinstance(version, int) or isinstance(version, bool) or version <= 0:
        errors.append("PROJECT.yaml template.version must be a positive integer")
    elif version > TEMPLATE_VERSION:
        errors.append(
            f"PROJECT.yaml template.version {version} is newer than supported {TEMPLATE_VERSION}"
        )
    revision = metadata.get("initialized_from_commit")
    if revision is not None and (not isinstance(revision, str) or not revision.strip()):
        errors.append("PROJECT.yaml template.initialized_from_commit must be null or non-empty")
    reviewed = metadata.get("reviewed_template_commit")
    if reviewed is not None and (not isinstance(reviewed, str) or not reviewed.strip()):
        errors.append("PROJECT.yaml template.reviewed_template_commit must be null or non-empty")
    migrations = metadata.get("applied_migrations")
    if not isinstance(migrations, list) or not all(
        isinstance(item, int) and not isinstance(item, bool) and item > 0 for item in migrations
    ):
        errors.append("PROJECT.yaml template.applied_migrations must be positive integers")
    elif len(migrations) != len(set(migrations)) or migrations != sorted(migrations):
        errors.append("PROJECT.yaml template.applied_migrations must be sorted and unique")
    elif isinstance(version, int) and any(item > version for item in migrations):
        errors.append("PROJECT.yaml applied migration cannot exceed template.version")

    if state.get("initialized") is False:
        if version != TEMPLATE_VERSION:
            errors.append(f"uninitialized template version must remain {TEMPLATE_VERSION}")
        if revision is not None:
            errors.append("uninitialized template initialized_from_commit must remain null")
        if reviewed is not None:
            errors.append("uninitialized template reviewed_template_commit must remain null")
        if migrations != []:
            errors.append("uninitialized template applied_migrations must remain empty")
    elif state.get("initialized") is True and revision is None:
        errors.append("initialized project must record template.initialized_from_commit")
    elif state.get("initialized") is True and reviewed is None and version >= 6:
        errors.append("initialized project must record template.reviewed_template_commit")
    return errors


def expected_state(root: Path) -> tuple[dict[str, Any], list[str]]:
    state = load_yaml(root / STATE_PATH)
    errors: list[str] = []
    if state.get("schema_version") != 1:
        errors.append("PROJECT.yaml schema_version must be 1")
    initialized = state.get("initialized")
    if not isinstance(initialized, bool):
        errors.append("PROJECT.yaml initialized must be boolean")
    template_version = (state.get("template") or {}).get("version", 0)
    for key in TEMPLATE_STATE:
        if key == "cli_name" and template_version < 3 and state.get("initialized") is True:
            continue
        if not isinstance(state.get(key), str) or not state[key].strip():
            errors.append(f"PROJECT.yaml {key} must be a non-empty string")
    errors.extend(template_metadata_errors(state))
    return state, errors


def workload_surface_errors(root: Path, package_name: str, cli_name: str) -> list[str]:
    errors: list[str] = []
    for relative in (
        f"src/{package_name}/workloads.py",
        "tools/workload.py",
        "tools/source_guard.py",
    ):
        if not (root / relative).is_file():
            errors.append(f"project workload boundary is missing: {relative}")
    smoke_path = root / "experiments/specs/smoke.yaml"
    if not smoke_path.is_file():
        errors.append("project workload boundary is missing: experiments/specs/smoke.yaml")
        return errors
    smoke = load_yaml(smoke_path)
    phases = smoke.get("phases", [])
    commands = (
        [smoke.get("command")]
        if "command" in smoke
        else [phase.get("command") for phase in phases if isinstance(phase, dict)]
    )
    expected_prefix = [cli_name, "workload"]
    if not commands or any(
        not isinstance(command, list) or len(command) < 3 or command[:2] != expected_prefix
        for command in commands
    ):
        errors.append(
            "experiments/specs/smoke.yaml must invoke the configured project workload CLI"
        )
    return errors


def check_project(root: Path = ROOT) -> list[str]:
    state, errors = expected_state(root)
    if errors:
        return errors
    if state["initialized"] is False:
        for key, value in TEMPLATE_STATE.items():
            if state[key] != value:
                errors.append(f"uninitialized template {key} must remain {value!r}")
        errors.extend(workload_surface_errors(root, state["package_name"], state["cli_name"]))
        return errors

    if state["template"]["version"] < TEMPLATE_VERSION:
        return [
            (
                f"project template version {state['template']['version']} requires migration to "
                f"{TEMPLATE_VERSION}"
            )
        ]

    identity = ProjectIdentity(
        project_name=state["project_name"],
        distribution_name=state["distribution_name"],
        package_name=state["package_name"],
        cli_name=state["cli_name"],
        contribution_id=state["contribution_id"],
    )
    try:
        validate_identity(identity)
    except ProjectCheckError as exc:
        errors.append(str(exc))
        return errors

    errors.extend(workload_surface_errors(root, identity.package_name, identity.cli_name))

    required = [
        f"src/{identity.package_name}/__init__.py",
        f"src/{identity.package_name}/workloads.py",
        "tests/smoke/test_project.py",
        "pyproject.toml",
        "CONTRIBUTIONS.md",
        "experiments/specs/smoke.yaml",
    ]
    for relative in required:
        if not (root / relative).is_file():
            errors.append(f"initialized project is missing: {relative}")

    checks = {
        "pyproject.toml": [
            f'name = "{identity.distribution_name}"',
            f'packages = ["src/{identity.package_name}", "tools"]',
            f'{identity.cli_name} = "tools.control_cli:main"',
        ],
        "CONTRIBUTIONS.md": [
            f"| {identity.contribution_id} |",
            f"`src/{identity.package_name}/`",
        ],
        "experiments/specs/smoke.yaml": [f"contribution: {identity.contribution_id}"],
        "tests/smoke/test_project.py": [f"from {identity.package_name} import project_status"],
        f"src/{identity.package_name}/workloads.py": ["project_status"],
    }
    for relative, required_text in checks.items():
        path = root / relative
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8")
        for text in required_text:
            if text not in content:
                errors.append(f"{relative} is inconsistent with PROJECT.yaml: missing {text!r}")

    residue_paths = [
        "pyproject.toml",
        "CONTRIBUTIONS.md",
        "experiments/specs/smoke.yaml",
        "tests/smoke/test_project.py",
        f"src/{identity.package_name}/__init__.py",
        f"src/{identity.package_name}/workloads.py",
        "Makefile",
        "README.md",
        "uv.lock",
    ]
    residues = (
        "agent-native-project",
        "src/project",
        "from project import",
        "contribution: bootstrap",
        "# Agent-Native Research Template",
        "## Initialize A Real Project",
        "## Repository Lifecycle Skills",
        "the bootstrap experiment",
        "template_status",
        "template/initialize_project.py",
        "template-test:",
        "template-e2e:",
        "make template-e2e",
    )
    for relative in residue_paths:
        path = root / relative
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8")
        for residue in residues:
            if residue in content:
                errors.append(
                    f"initialized project retains template residue in {relative}: {residue}"
                )
    template_cli_entry = f'{TEMPLATE_STATE["cli_name"]} = "tools.control_cli:main"'
    if identity.cli_name != TEMPLATE_STATE["cli_name"]:
        pyproject_content = (root / "pyproject.toml").read_text(encoding="utf-8")
        if template_cli_entry in pyproject_content:
            errors.append("initialized project retains template CLI entry")
    for relative in ("src/project", "tests/smoke/test_template.py", "template"):
        if (root / relative).exists():
            errors.append(f"initialized project retains template-only path: {relative}")
    return errors


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(description="Check project identity and template provenance.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("check", help="check identity and retained downstream surfaces")
    subparsers.add_parser("compatibility", help="check registered template compatibility")
    migrate = subparsers.add_parser("migrate", help="apply a registered forward migration")
    migrate.add_argument("--to", type=int, required=True)
    migrate.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if args.command in {"compatibility", "migrate"}:
        from . import template_compat

        forwarded = (
            ["check"] if args.command == "compatibility" else ["migrate", "--to", str(args.to)]
        )
        if args.command == "migrate" and args.dry_run:
            forwarded.append("--dry-run")
        return template_compat.main(forwarded, root)
    try:
        errors = check_project(root)
        if errors:
            for error in errors:
                print(f"ERROR {error}")
            return 1
        state = load_yaml(root / STATE_PATH)
        label = "initialized project" if state["initialized"] else "template bootstrap"
        print(f"OK {label} identity and paths")
        return 0
    except (OSError, ProjectCheckError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
