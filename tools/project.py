from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from repo_cli import project as _canonical

CLI_PATTERN = _canonical.CLI_PATTERN
CONTRIBUTION_PATTERN = _canonical.CONTRIBUTION_PATTERN
DISTRIBUTION_PATTERN = _canonical.DISTRIBUTION_PATTERN
PACKAGE_PATTERN = _canonical.PACKAGE_PATTERN
STATE_PATH = _canonical.STATE_PATH
TEMPLATE_NAME = _canonical.TEMPLATE_NAME
TEMPLATE_STATE = _canonical.TEMPLATE_STATE
TEMPLATE_VERSION = _canonical.TEMPLATE_VERSION
ProjectCheckError = _canonical.ProjectCheckError
ProjectIdentity = _canonical.ProjectIdentity
check_project = _canonical.check_project
dump_yaml = _canonical.dump_yaml
expected_state = _canonical.expected_state
load_yaml = _canonical.load_yaml
template_metadata_errors = _canonical.template_metadata_errors
validate_identity = _canonical.validate_identity
workload_surface_errors = _canonical.workload_surface_errors
write_text = _canonical.write_text
canonical_main = _canonical.main


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(
        description="Compatibility adapter for project checks and template migration commands."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("check", help="delegate to the canonical repository project checker")
    subparsers.add_parser("compatibility", help="check registered template compatibility")
    migrate = subparsers.add_parser("migrate", help="apply a registered forward migration")
    migrate.add_argument("--to", type=int, required=True)
    migrate.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "check":
        return canonical_main(["check"], root)

    from . import template_compat

    forwarded = (
        ["check"] if args.command == "compatibility" else ["migrate", "--to", str(args.to)]
    )
    if args.command == "migrate" and args.dry_run:
        forwarded.append("--dry-run")
    return template_compat.main(forwarded, root)


if __name__ == "__main__":
    raise SystemExit(main())
