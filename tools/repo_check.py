from __future__ import annotations

import subprocess
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
UNIT_MANIFEST = ROOT / "REPO_UNITS.yaml"
UNIT_NAMES = {"governance", "functional"}
IGNORED_PARTS = {".git", ".venv", ".pytest_cache", ".ruff_cache", "runs", "artifacts"}
REQUIRED_EXPERIMENT_FIELDS = {
    "id",
    "contribution",
    "config",
    "environment",
    "executor",
    "evaluation",
    "command",
}


def project_files() -> list[Path]:
    return sorted(
        path
        for path in ROOT.rglob("*")
        if path.is_file()
        and not any(part in IGNORED_PARTS for part in path.relative_to(ROOT).parts)
    )


def tracked_files() -> set[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return set()
    return {line for line in result.stdout.splitlines() if line}


def repository_files() -> set[str]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return set()
    return {line for line in result.stdout.splitlines() if line}


def load_yaml(path: Path, errors: list[str]) -> object:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        errors.append(f"YAML-001 {path.relative_to(ROOT)}: {exc}")
        return None


def is_valid_repo_path(value: object) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    path = Path(value.rstrip("/"))
    return not path.is_absolute() and ".." not in path.parts


def load_unit_manifest(errors: list[str]) -> dict[str, object] | None:
    data = load_yaml(UNIT_MANIFEST, errors)
    if not isinstance(data, dict):
        errors.append("UNIT-001 REPO_UNITS.yaml must be a mapping")
        return None
    if data.get("schema_version") != 1:
        errors.append("UNIT-002 REPO_UNITS.yaml schema_version must be 1")

    units = data.get("units")
    if not isinstance(units, dict) or set(units) != UNIT_NAMES:
        errors.append("UNIT-003 units must contain exactly governance and functional")

    ownership = data.get("ownership")
    if not isinstance(ownership, dict):
        errors.append("UNIT-004 ownership must be a mapping")
        return data
    if ownership.get("default") != "functional":
        errors.append("UNIT-005 ownership.default must be functional")

    governance_paths = ownership.get("governance_paths")
    if not isinstance(governance_paths, list) or not governance_paths:
        errors.append("UNIT-006 ownership.governance_paths must be a non-empty list")
    elif any(not is_valid_repo_path(path) for path in governance_paths):
        errors.append("UNIT-007 governance paths must be normalized repository-relative paths")
    elif len(governance_paths) != len(set(governance_paths)):
        errors.append("UNIT-008 governance paths must be unique")

    required_paths = data.get("required_paths")
    if not isinstance(required_paths, dict) or set(required_paths) != UNIT_NAMES:
        errors.append("UNIT-009 required_paths must contain governance and functional")
    else:
        for unit, paths in required_paths.items():
            if not isinstance(paths, list) or any(not is_valid_repo_path(path) for path in paths):
                errors.append(f"UNIT-010 required_paths.{unit} must contain valid repository paths")

    return data


def governance_paths(manifest: dict[str, object]) -> list[str]:
    ownership = manifest.get("ownership")
    if not isinstance(ownership, dict):
        return []
    paths = ownership.get("governance_paths")
    if not isinstance(paths, list):
        return []
    return [path for path in paths if isinstance(path, str)]


def classify_path(relative_path: str, manifest: dict[str, object]) -> str:
    for rule in governance_paths(manifest):
        if rule.endswith("/"):
            if relative_path.startswith(rule):
                return "governance"
        elif relative_path == rule:
            return "governance"
    return "functional"


def check_repository_units(manifest: dict[str, object], errors: list[str]) -> Counter[str]:
    files = repository_files()
    counts = Counter(classify_path(path, manifest) for path in files)

    for rule in governance_paths(manifest):
        if rule.endswith("/"):
            matched = any(path.startswith(rule) for path in files)
        else:
            matched = rule in files
        if not matched:
            errors.append(f"UNIT-011 governance path matches no repository file: {rule}")

    required_paths = manifest.get("required_paths")
    if not isinstance(required_paths, dict):
        return counts
    for unit in sorted(UNIT_NAMES):
        paths = required_paths.get(unit)
        if not isinstance(paths, list):
            continue
        for relative_path in paths:
            if not isinstance(relative_path, str):
                continue
            path = ROOT / relative_path
            if not path.exists():
                errors.append(f"STRUCT-001 missing required path: {relative_path}")
                continue
            actual_unit = classify_path(relative_path.rstrip("/"), manifest)
            if actual_unit != unit:
                errors.append(
                    f"UNIT-012 {relative_path} is required by {unit} but owned by {actual_unit}"
                )
    return counts


def check_yaml(errors: list[str]) -> None:
    for path in project_files():
        if path.suffix in {".yaml", ".yml"}:
            load_yaml(path, errors)


def check_skills(errors: list[str]) -> None:
    skill_root = ROOT / ".agents" / "skills"
    seen_names: set[str] = set()
    for skill_file in sorted(skill_root.glob("*/SKILL.md")):
        text = skill_file.read_text(encoding="utf-8")
        if not text.startswith("---\n") or "\n---\n" not in text[4:]:
            errors.append(f"SKILL-001 invalid frontmatter: {skill_file.relative_to(ROOT)}")
            continue
        frontmatter_text = text.split("---\n", 2)[1]
        metadata = yaml.safe_load(frontmatter_text)
        if not isinstance(metadata, dict):
            errors.append(f"SKILL-002 invalid metadata: {skill_file.relative_to(ROOT)}")
            continue
        name = metadata.get("name")
        description = metadata.get("description")
        if name != skill_file.parent.name:
            errors.append(
                f"SKILL-003 name {name!r} does not match directory {skill_file.parent.name!r}"
            )
        if not isinstance(description, str) or not description.strip():
            errors.append(f"SKILL-004 missing description: {skill_file.relative_to(ROOT)}")
        if isinstance(name, str) and name in seen_names:
            errors.append(f"SKILL-005 duplicate skill name: {name}")
        if isinstance(name, str):
            seen_names.add(name)


def check_experiment_specs(errors: list[str]) -> None:
    for path in sorted((ROOT / "experiments" / "specs").glob("*.yaml")):
        data = load_yaml(path, errors)
        if not isinstance(data, dict):
            errors.append(f"EXP-001 experiment spec must be a mapping: {path.relative_to(ROOT)}")
            continue
        missing = REQUIRED_EXPERIMENT_FIELDS - data.keys()
        if missing:
            errors.append(
                f"EXP-002 {path.relative_to(ROOT)} missing fields: {', '.join(sorted(missing))}"
            )


def check_tracked_state(errors: list[str]) -> None:
    for relative_path in sorted(tracked_files()):
        path = ROOT / relative_path
        if relative_path.startswith("runs/"):
            errors.append(f"GIT-001 run output must not be tracked: {relative_path}")
        if relative_path.startswith(".agents/runtime/") and relative_path != (
            ".agents/runtime/.gitignore"
        ):
            errors.append(f"GIT-002 runtime state must not be tracked: {relative_path}")
        if path.is_file() and path.stat().st_size > 10 * 1024 * 1024:
            errors.append(f"GIT-003 tracked file exceeds 10 MiB: {relative_path}")


def main() -> int:
    errors: list[str] = []
    manifest = load_unit_manifest(errors)
    unit_counts: Counter[str] = Counter()
    if manifest is not None:
        unit_counts = check_repository_units(manifest, errors)
    check_yaml(errors)
    check_skills(errors)
    check_experiment_specs(errors)
    check_tracked_state(errors)

    if errors:
        for error in errors:
            print(f"ERROR {error}")
        return 1

    print(
        "OK repository structure, units "
        f"(functional={unit_counts['functional']}, governance={unit_counts['governance']}), "
        "YAML, skills, experiment specs, and tracked state"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
