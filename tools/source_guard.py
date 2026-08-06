from __future__ import annotations

import hashlib
import os
from pathlib import Path

PROTECTED_PATHS = (
    "PROJECT.yaml",
    "pyproject.toml",
    "Makefile",
    "CONTRIBUTIONS.md",
    "src",
    "repo_cli",
    "tests",
    "tools",
    "configs",
    "environments",
    "evals",
    "experiments",
    "infra",
    "schemas",
)
IGNORED_PARTS = {"__pycache__", ".pytest_cache", ".ruff_cache"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}


def file_identity(path: Path) -> str:
    if path.is_symlink():
        return "symlink:" + os.readlink(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protected_snapshot(root: Path) -> dict[str, str]:
    records: dict[str, str] = {}
    for relative in PROTECTED_PATHS:
        path = root / relative
        if path.is_file() or path.is_symlink():
            records[relative] = file_identity(path)
            continue
        if not path.is_dir():
            continue
        for candidate in sorted(path.rglob("*")):
            candidate_relative = candidate.relative_to(root)
            if any(part in IGNORED_PARTS for part in candidate_relative.parts):
                continue
            if candidate.suffix in IGNORED_SUFFIXES or not (
                candidate.is_file() or candidate.is_symlink()
            ):
                continue
            records[candidate_relative.as_posix()] = file_identity(candidate)
    return records


def mutation_errors(before: dict[str, str], after: dict[str, str]) -> list[str]:
    errors: list[str] = []
    for path in sorted(before.keys() | after.keys()):
        if path not in before:
            errors.append(f"protected project file created: {path}")
        elif path not in after:
            errors.append(f"protected project file removed: {path}")
        elif before[path] != after[path]:
            errors.append(f"protected project file changed: {path}")
    return errors
