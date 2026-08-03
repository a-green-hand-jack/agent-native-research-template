from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import initialize_project

ROOT = Path(__file__).resolve().parents[1]
Migration = Callable[[Path, dict[str, Any]], list[str]]
MIGRATIONS: dict[int, Migration] = {}


class TemplateCompatibilityError(ValueError):
    """Raised when template provenance is missing, incompatible, or cannot be migrated."""


def compatibility_errors(root: Path = ROOT) -> list[str]:
    state, errors = initialize_project.expected_state(root)
    if errors:
        return errors
    metadata = state["template"]
    version = metadata["version"]
    if version < initialize_project.TEMPLATE_VERSION:
        errors.append(
            f"project template version {version} requires migration to "
            f"{initialize_project.TEMPLATE_VERSION}"
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
    if target > initialize_project.TEMPLATE_VERSION:
        raise TemplateCompatibilityError(
            f"target template version {target} is newer than supported "
            f"{initialize_project.TEMPLATE_VERSION}"
        )
    plan = list(range(current + 1, target + 1))
    missing = [version for version in plan if version not in MIGRATIONS]
    if missing:
        rendered = ", ".join(str(version) for version in missing)
        raise TemplateCompatibilityError(f"missing migration implementations for: {rendered}")
    return plan


def migrate(root: Path, target: int, *, dry_run: bool = False) -> list[str]:
    state, errors = initialize_project.expected_state(root)
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
    initialize_project.write_text(
        root / initialize_project.STATE_PATH,
        initialize_project.dump_yaml(state),
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
            state = initialize_project.load_yaml(root / initialize_project.STATE_PATH)
            print(
                "OK template compatibility "
                f"version={state['template']['version']} "
                f"current={initialize_project.TEMPLATE_VERSION}"
            )
            return 0
        changes = migrate(root, args.to, dry_run=args.dry_run)
        if changes:
            for change in changes:
                print(change)
        else:
            print(f"OK no migration required for template version {args.to}")
        return 0
    except (OSError, TemplateCompatibilityError, initialize_project.InitializationError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
