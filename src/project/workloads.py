from __future__ import annotations

import argparse

from . import template_status


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Project workload entry points.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("smoke", help="run the smallest project workload")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "smoke":
        print(template_status())
        return 0
    raise AssertionError(f"unhandled workload command: {args.command}")
