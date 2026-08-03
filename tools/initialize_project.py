from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = "PROJECT.yaml"
TEMPLATE_NAME = "agent-native-research-template"
TEMPLATE_VERSION = 2
TEMPLATE_STATE = {
    "project_name": "Agent-Native Research Template",
    "distribution_name": "agent-native-project",
    "package_name": "project",
    "contribution_id": "bootstrap",
}
DISTRIBUTION_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PACKAGE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
CONTRIBUTION_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


class InitializationError(ValueError):
    """Raised when template initialization would be incomplete or unsafe."""


@dataclass(frozen=True)
class ProjectIdentity:
    project_name: str
    distribution_name: str
    package_name: str
    contribution_id: str


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise InitializationError(f"cannot read {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise InitializationError(f"{path} must contain a YAML mapping")
    return data


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def dump_yaml(data: dict[str, Any]) -> str:
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)


def git_revision(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        errors="replace",
    )
    revision = result.stdout.strip()
    return revision if result.returncode == 0 and revision else "unknown"


def validate_identity(identity: ProjectIdentity) -> None:
    if not identity.project_name.strip():
        raise InitializationError("project name must not be empty")
    if not DISTRIBUTION_PATTERN.fullmatch(identity.distribution_name):
        raise InitializationError(
            "distribution name must use lowercase letters, digits, and single hyphens"
        )
    if not PACKAGE_PATTERN.fullmatch(identity.package_name):
        raise InitializationError("package name must be a lowercase Python identifier")
    if not CONTRIBUTION_PATTERN.fullmatch(identity.contribution_id):
        raise InitializationError("contribution ID must be a stable lowercase identifier")
    if identity.distribution_name == TEMPLATE_STATE["distribution_name"]:
        raise InitializationError("distribution name must replace the template value")
    if identity.package_name == TEMPLATE_STATE["package_name"]:
        raise InitializationError("package name must replace the template value")
    if identity.contribution_id == TEMPLATE_STATE["contribution_id"]:
        raise InitializationError("contribution ID must replace the template value")


def replace_required(content: str, old: str, new: str, path: str) -> str:
    if old not in content:
        raise InitializationError(f"expected template text is missing from {path}: {old!r}")
    return content.replace(old, new)


def read_required(root: Path, relative: str) -> str:
    path = root / relative
    if not path.is_file():
        raise InitializationError(f"required template path is missing: {relative}")
    return path.read_text(encoding="utf-8")


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
        if migrations != []:
            errors.append("uninitialized template applied_migrations must remain empty")
    elif state.get("initialized") is True and revision is None:
        errors.append("initialized project must record template.initialized_from_commit")
    return errors


def expected_state(root: Path) -> tuple[dict[str, Any], list[str]]:
    state = load_yaml(root / STATE_PATH)
    errors: list[str] = []
    if state.get("schema_version") != 1:
        errors.append("PROJECT.yaml schema_version must be 1")
    initialized = state.get("initialized")
    if not isinstance(initialized, bool):
        errors.append("PROJECT.yaml initialized must be boolean")
    for key in TEMPLATE_STATE:
        if not isinstance(state.get(key), str) or not state[key].strip():
            errors.append(f"PROJECT.yaml {key} must be a non-empty string")
    errors.extend(template_metadata_errors(state))
    return state, errors


def build_changes(root: Path, identity: ProjectIdentity) -> dict[str, str]:
    validate_identity(identity)
    state, errors = expected_state(root)
    if errors:
        raise InitializationError("; ".join(errors))
    if state.get("initialized") is True:
        raise InitializationError("project is already initialized")

    pyproject = read_required(root, "pyproject.toml")
    pyproject = replace_required(
        pyproject,
        'name = "agent-native-project"',
        f'name = "{identity.distribution_name}"',
        "pyproject.toml",
    )
    pyproject = replace_required(
        pyproject,
        'description = "Bootstrap package for an agent-native research project"',
        f'description = "{identity.project_name}"',
        "pyproject.toml",
    )
    pyproject = replace_required(
        pyproject,
        'packages = ["src/project"]',
        f'packages = ["src/{identity.package_name}"]',
        "pyproject.toml",
    )

    uv_lock = read_required(root, "uv.lock").replace(
        'name = "agent-native-project"', f'name = "{identity.distribution_name}"'
    )

    contributions = read_required(root, "CONTRIBUTIONS.md")
    old_row = (
        "| bootstrap | Replace with the first real contribution | `src/project/` | "
        "`configs/base.yaml` | `evals/smoke.yaml` | bootstrap |"
    )
    new_row = (
        f"| {identity.contribution_id} | {identity.project_name} initial vertical slice | "
        f"`src/{identity.package_name}/` | `configs/base.yaml` | `evals/smoke.yaml` | active |"
    )
    contributions = replace_required(contributions, old_row, new_row, "CONTRIBUTIONS.md")

    spec = read_required(root, "experiments/specs/smoke.yaml")
    spec = replace_required(
        spec,
        "contribution: bootstrap",
        f"contribution: {identity.contribution_id}",
        "experiments/specs/smoke.yaml",
    )

    source = read_required(root, "src/project/__init__.py")
    source = replace_required(
        source,
        '"""Bootstrap package. Replace this module with the first real project slice."""',
        f'"""{identity.project_name} package."""',
        "src/project/__init__.py",
    )
    source = source.replace("template_status", "project_status")
    source = source.replace("bootstrap smoke test", "initialized smoke test")

    smoke_test = read_required(root, "tests/smoke/test_template.py")
    smoke_test = smoke_test.replace("from project import", f"from {identity.package_name} import")
    smoke_test = smoke_test.replace("template_status", "project_status")
    smoke_test = smoke_test.replace("test_template_vertical_slice", "test_project_vertical_slice")

    revision = git_revision(root)
    readme = read_required(root, "README.md")
    readme = replace_required(
        readme,
        "# Agent-Native Research Template",
        f"# {identity.project_name}",
        "README.md",
    )
    marker = (
        f"\n> Initialized from Agent-Native Research Template v{TEMPLATE_VERSION} at "
        f"`{revision}`. Distribution: `{identity.distribution_name}`; package: "
        f"`{identity.package_name}`.\n"
    )
    first_break = readme.find("\n")
    readme = readme[: first_break + 1] + marker + readme[first_break + 1 :]

    initialized_state = {
        "schema_version": 1,
        "initialized": True,
        "project_name": identity.project_name,
        "distribution_name": identity.distribution_name,
        "package_name": identity.package_name,
        "contribution_id": identity.contribution_id,
        "template": {
            "name": TEMPLATE_NAME,
            "version": TEMPLATE_VERSION,
            "initialized_from_commit": revision,
            "applied_migrations": [],
        },
    }
    return {
        STATE_PATH: dump_yaml(initialized_state),
        "pyproject.toml": pyproject,
        "uv.lock": uv_lock,
        "CONTRIBUTIONS.md": contributions,
        "experiments/specs/smoke.yaml": spec,
        f"src/{identity.package_name}/__init__.py": source,
        "tests/smoke/test_project.py": smoke_test,
        "README.md": readme,
    }


def apply_changes(root: Path, identity: ProjectIdentity, *, dry_run: bool = False) -> list[str]:
    changes = build_changes(root, identity)
    removed = ["src/project/__init__.py", "tests/smoke/test_template.py"]
    targets = set(changes)
    for relative in removed:
        if relative not in targets and not (root / relative).is_file():
            raise InitializationError(f"required source path disappeared before apply: {relative}")
    planned = [f"write {path}" for path in sorted(changes)] + [f"remove {path}" for path in removed]
    if dry_run:
        return planned
    for relative, content in changes.items():
        write_text(root / relative, content)
    for relative in removed:
        path = root / relative
        if path.exists() and relative not in changes:
            path.unlink()
            parent = path.parent
            if parent != root and not any(parent.iterdir()):
                parent.rmdir()
    return planned


def check_project(root: Path = ROOT) -> list[str]:
    state, errors = expected_state(root)
    if errors:
        return errors
    if state["initialized"] is False:
        for key, value in TEMPLATE_STATE.items():
            if state[key] != value:
                errors.append(f"uninitialized template {key} must remain {value!r}")
        return errors

    identity = ProjectIdentity(
        project_name=state["project_name"],
        distribution_name=state["distribution_name"],
        package_name=state["package_name"],
        contribution_id=state["contribution_id"],
    )
    try:
        validate_identity(identity)
    except InitializationError as exc:
        errors.append(str(exc))
        return errors

    required = [
        f"src/{identity.package_name}/__init__.py",
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
            f'packages = ["src/{identity.package_name}"]',
        ],
        "CONTRIBUTIONS.md": [
            f"| {identity.contribution_id} |",
            f"`src/{identity.package_name}/`",
        ],
        "experiments/specs/smoke.yaml": [f"contribution: {identity.contribution_id}"],
        "tests/smoke/test_project.py": [f"from {identity.package_name} import project_status"],
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
        "uv.lock",
    ]
    residues = (
        "agent-native-project",
        "src/project",
        "from project import",
        "contribution: bootstrap",
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
    if (root / "src/project").exists():
        errors.append("initialized project retains src/project")
    if (root / "tests/smoke/test_template.py").exists():
        errors.append("initialized project retains tests/smoke/test_template.py")
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Initialize and validate a repository template.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    apply = subparsers.add_parser("apply", help="replace bootstrap project identity")
    apply.add_argument("--project-name", required=True)
    apply.add_argument("--distribution-name", required=True)
    apply.add_argument("--package-name", required=True)
    apply.add_argument("--contribution-id", required=True)
    apply.add_argument("--dry-run", action="store_true")

    subparsers.add_parser("check", help="check template or initialized project consistency")
    return parser


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "check":
            errors = check_project(root)
            if errors:
                for error in errors:
                    print(f"ERROR {error}")
                return 1
            state = load_yaml(root / STATE_PATH)
            label = "initialized project" if state["initialized"] else "template bootstrap"
            print(f"OK {label} identity and paths")
            return 0
        identity = ProjectIdentity(
            project_name=args.project_name,
            distribution_name=args.distribution_name,
            package_name=args.package_name,
            contribution_id=args.contribution_id,
        )
        planned = apply_changes(root, identity, dry_run=args.dry_run)
        for item in planned:
            print(item)
        return 0
    except (InitializationError, OSError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
