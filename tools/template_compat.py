from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

try:
    from . import project
except ImportError:  # compatibility for direct script execution
    import project

ROOT = Path(__file__).resolve().parents[1]
Migration = Callable[[Path, dict[str, Any]], list[str]]


def migrate_to_v2(root: Path, _: dict[str, Any]) -> list[str]:
    relative = "experiments/specs/smoke.yaml"
    path = root / relative
    specification = project.load_yaml(path)
    if "inputs" in specification:
        return []
    specification["inputs"] = [{"id": "smoke-source", "kind": "path", "path": "src"}]
    project.write_text(path, project.dump_yaml(specification))
    return [f"write {relative}"]


def migrate_to_v3(root: Path, state: dict[str, Any]) -> list[str]:
    cli_name = state["distribution_name"]
    if not project.CLI_PATTERN.fullmatch(cli_name):
        raise TemplateCompatibilityError(
            "distribution_name cannot be used as a CLI name; choose a valid lowercase hyphenated name"
        )
    state["cli_name"] = cli_name
    changes: list[str] = []

    pyproject_path = root / "pyproject.toml"
    content = pyproject_path.read_text(encoding="utf-8")
    runtime_dependencies = 'dependencies = [\n    "jsonschema>=4.23",\n    "pyyaml>=6.0",\n]'
    content = content.replace('    "jsonschema>=4.23",\n', "")
    content = content.replace('    "pyyaml>=6.0",\n', "")
    if "dependencies = []" in content:
        content = content.replace("dependencies = []", runtime_dependencies)
    configured_entry = f'{cli_name} = "tools.control_cli:main"'
    template_entry = 'researchctl = "tools.control_cli:main"'
    if template_entry in content:
        content = content.replace(template_entry, configured_entry)
    elif configured_entry not in content:
        marker = "[dependency-groups]"
        if marker not in content:
            raise TemplateCompatibilityError("pyproject.toml has no dependency-groups section")
        content = content.replace(marker, f"[project.scripts]\n{configured_entry}\n\n{marker}")
    package_marker = f'packages = ["src/{state["package_name"]}"]'
    package_replacement = f'packages = ["src/{state["package_name"]}", "tools"]'
    if package_marker in content:
        content = content.replace(package_marker, package_replacement)
    elif package_replacement not in content:
        raise TemplateCompatibilityError("pyproject.toml does not expose the initialized package")
    project.write_text(pyproject_path, content)
    changes.append("write pyproject.toml")

    makefile_path = root / "Makefile"
    if makefile_path.is_file():
        makefile = makefile_path.read_text(encoding="utf-8")
        makefile = makefile.replace(
            "uv run python tools/research.py validate\n	uv run python tools/evidence.py validate",
            f"uv run {cli_name} experiment validate",
        )
        makefile = makefile.replace(
            "uv run python tools/evidence.py run experiments/specs/smoke.yaml",
            f"uv run {cli_name} experiment run experiments/specs/smoke.yaml",
        )
        if "control-cli:" not in makefile:
            makefile = makefile.replace(
                "research-validate:\n",
                f"control-cli:\n	uv run {cli_name} --help >/dev/null\n\nresearch-validate:\n",
            )
            makefile = makefile.replace("verify: ", "verify: control-cli ")
        project.write_text(makefile_path, makefile)
        changes.append("write Makefile")

    readme_path = root / "README.md"
    if readme_path.is_file():
        readme = readme_path.read_text(encoding="utf-8")
        readme = readme.replace(
            "uv run python tools/research.py validate", f"uv run {cli_name} experiment validate"
        )
        readme = readme.replace(
            "uv run python tools/evidence.py ", f"uv run {cli_name} experiment "
        )
        readme = readme.replace("uv run python tools/archive.py ", f"uv run {cli_name} archive ")
        project.write_text(readme_path, readme)
        changes.append("write README.md")
    return changes


def migrate_to_v4(root: Path, state: dict[str, Any]) -> list[str]:
    changes: list[str] = []
    spec_path = root / "experiments/specs/smoke.yaml"
    if spec_path.is_file():
        spec = project.load_yaml(spec_path)
        if spec.get("phases") and "command" in spec:
            spec.pop("command")
            project.write_text(spec_path, project.dump_yaml(spec))
            changes.append("write experiments/specs/smoke.yaml")
    evaluation_path = root / "evals/smoke.yaml"
    if evaluation_path.is_file():
        evaluation = project.load_yaml(evaluation_path)
        if "command" in evaluation:
            evaluation.pop("command")
            project.write_text(evaluation_path, project.dump_yaml(evaluation))
            changes.append("write evals/smoke.yaml")
    profile_path = root / "infra/profiles/local.yaml"
    if profile_path.is_file():
        profile = project.load_yaml(profile_path)
        profile.setdefault("environment", {"PYTHONUNBUFFERED": "1"})
        profile.setdefault("inherit_environment", ["PATH", "HOME"])
        project.write_text(profile_path, project.dump_yaml(profile))
        changes.append("write infra/profiles/local.yaml")
    return changes


def migrate_to_v5(root: Path, state: dict[str, Any]) -> list[str]:
    return []


def migrate_to_v6(root: Path, state: dict[str, Any]) -> list[str]:
    metadata = state["template"]
    if metadata.get("reviewed_template_commit") is None:
        metadata["reviewed_template_commit"] = metadata["initialized_from_commit"]
    return []


def migrate_to_v7(root: Path, state: dict[str, Any]) -> list[str]:
    package_name = state["package_name"]
    cli_name = state["cli_name"]
    blockers: list[str] = []
    workload_path = root / "src" / package_name / "workloads.py"
    if not workload_path.is_file():
        blockers.append(f"missing src/{package_name}/workloads.py")
    for path in sorted((root / "experiments" / "specs").rglob("*.yaml")):
        spec = project.load_yaml(path)
        commands = (
            [spec.get("command")]
            if "command" in spec
            else [phase.get("command") for phase in spec.get("phases", [])]
        )
        expected = [cli_name, "workload"]
        if not commands or any(
            not isinstance(command, list) or len(command) < 3 or command[:2] != expected
            for command in commands
        ):
            blockers.append(
                f"{path.relative_to(root).as_posix()} must use {cli_name} workload <command>"
            )
    if blockers:
        raise TemplateCompatibilityError(
            "template v7 requires a reviewed workload CLI migration: " + "; ".join(blockers)
        )
    return []


MIGRATIONS: dict[int, Migration] = {
    2: migrate_to_v2,
    3: migrate_to_v3,
    4: migrate_to_v4,
    5: migrate_to_v5,
    6: migrate_to_v6,
    7: migrate_to_v7,
}


class TemplateCompatibilityError(ValueError):
    """Raised when template provenance is missing, incompatible, or cannot be migrated."""


def compatibility_errors(root: Path = ROOT) -> list[str]:
    state, errors = project.expected_state(root)
    if errors:
        return errors
    metadata = state["template"]
    version = metadata["version"]
    if version < project.TEMPLATE_VERSION:
        errors.append(
            f"project template version {version} requires migration to {project.TEMPLATE_VERSION}"
        )
    return errors


def migration_plan(state: dict[str, Any], target: int) -> list[int]:
    if not isinstance(target, int) or isinstance(target, bool) or target <= 0:
        raise TemplateCompatibilityError("migration target must be a positive integer")
    current = state["template"]["version"]
    if target < current:
        raise TemplateCompatibilityError(
            f"template migrations are forward-only: current={current}, target={target}"
        )
    if target > project.TEMPLATE_VERSION:
        raise TemplateCompatibilityError(
            f"target template version {target} is newer than supported {project.TEMPLATE_VERSION}"
        )
    plan = list(range(current + 1, target + 1))
    missing = [version for version in plan if version not in MIGRATIONS]
    if missing:
        rendered = ", ".join(str(version) for version in missing)
        raise TemplateCompatibilityError(f"missing migration implementations for: {rendered}")
    return plan


def migrate(root: Path, target: int, *, dry_run: bool = False) -> list[str]:
    state, errors = project.expected_state(root)
    if errors:
        raise TemplateCompatibilityError("; ".join(errors))
    if state["initialized"] is not True:
        raise TemplateCompatibilityError(
            "initialize the project before applying downstream template migrations"
        )
    plan = migration_plan(state, target)
    if dry_run:
        return [f"apply template migration {version}" for version in plan]

    changes: list[str] = []
    metadata = state["template"]
    applied = list(metadata["applied_migrations"])
    for version in plan:
        changes.extend(MIGRATIONS[version](root, state))
        metadata["version"] = version
        if version not in applied:
            applied.append(version)
        metadata["applied_migrations"] = sorted(applied)
    project.write_text(
        root / project.STATE_PATH,
        project.dump_yaml(state),
    )
    remaining = compatibility_errors(root)
    if remaining:
        raise TemplateCompatibilityError(
            "migration left an incompatible state: " + "; ".join(remaining)
        )
    return changes


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check and explicitly migrate template provenance metadata."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("check", help="check compatibility with this template toolset")
    migrate_parser = subparsers.add_parser(
        "migrate",
        help="apply registered forward migrations to an initialized project",
    )
    migrate_parser.add_argument("--to", type=int, required=True)
    migrate_parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "check":
            errors = compatibility_errors(root)
            if errors:
                for error in errors:
                    print(f"ERROR {error}")
                return 1
            state = project.load_yaml(root / project.STATE_PATH)
            print(
                "OK template compatibility "
                f"version={state['template']['version']} "
                f"current={project.TEMPLATE_VERSION}"
            )
            return 0
        changes = migrate(root, args.to, dry_run=args.dry_run)
        if changes:
            for change in changes:
                print(change)
        else:
            print(f"OK no migration required for template version {args.to}")
        return 0
    except (OSError, TemplateCompatibilityError, project.ProjectCheckError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
