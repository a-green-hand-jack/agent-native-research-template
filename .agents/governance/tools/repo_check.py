from __future__ import annotations

import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
UNIT_MANIFEST = ROOT / ".agents" / "governance" / "REPO_UNITS.yaml"
UNIT_NAMES = {"governance", "functional"}
IGNORED_PARTS = {
    ".git",
    ".omx",
    ".venv",
    ".pytest_cache",
    ".ruff_cache",
    "runs",
    "artifacts",
}
GOVERNANCE_PATHS = {".agents/", "AGENTS.md"}
TOOL_RUNTIME_PREFIXES = {".omx/"}
OVERLAY_MARKER = re.compile(r"<!--\s*(?P<name>[A-Z][A-Z0-9:_-]*):(?P<boundary>START|END)\s*-->")
LEGACY_GOVERNANCE_PATHS = {
    "ANATOMY.md",
    "CONTRACT.md",
    "GUIDE.md",
    "REPO_UNITS.yaml",
    "docs/governance",
    "tools/repo_check.py",
}
FUNCTIONAL_EXECUTION_ROOTS = {
    "configs",
    "environments",
    "evals",
    "experiments",
    "infra",
    "src",
    "tests",
}
FUNCTIONAL_COMMAND_FILES = {"Makefile", "pyproject.toml", ".pre-commit-config.yaml"}
TEXT_SUFFIXES = {".md", ".py", ".sh", ".toml", ".yaml", ".yml"}
REQUIRED_EXPERIMENT_FIELDS = {
    "id",
    "contribution",
    "config",
    "environment",
    "executor",
    "evaluation",
}
DEV_GUIDE_PATH = ".agents/skills/dev-guide/SKILL.md"
INITIALIZE_PROJECT_SKILL = ".agents/skills/initialize-project/SKILL.md"
ADOPT_TEMPLATE_SKILL = ".agents/skills/adopt-research-template/SKILL.md"
UPDATE_TEMPLATE_SKILL = ".agents/skills/update-from-template/SKILL.md"
INFLUENCES_PATH = ".agents/governance/INFLUENCES.md"
LIFECYCLE_SKILLS = (
    INITIALIZE_PROJECT_SKILL,
    ADOPT_TEMPLATE_SKILL,
    UPDATE_TEMPLATE_SKILL,
)
GUIDANCE_ROUTES = {
    "README.md": (INFLUENCES_PATH, *LIFECYCLE_SKILLS),
    "AGENTS.md": (DEV_GUIDE_PATH, INFLUENCES_PATH),
    DEV_GUIDE_PATH: (
        ".agents/governance/ANATOMY.md",
        ".agents/governance/CONTRACT.md",
        ".agents/governance/REPO_UNITS.yaml",
        ".agents/governance/GUIDE.md",
        *LIFECYCLE_SKILLS,
    ),
    INITIALIZE_PROJECT_SKILL: (
        ADOPT_TEMPLATE_SKILL,
        UPDATE_TEMPLATE_SKILL,
        "tools/initialize_project.py",
        "tools/template_compat.py",
        "--cli-name",
    ),
    UPDATE_TEMPLATE_SKILL: (
        ADOPT_TEMPLATE_SKILL,
        "PROJECT.yaml",
        "tools/template_compat.py",
    ),
    INFLUENCES_PATH: (
        "https://lingtai.ai/",
        "https://lingtai.ai/en/about/",
    ),
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
    manifest_name = UNIT_MANIFEST.relative_to(ROOT)
    if not isinstance(data, dict):
        errors.append(f"UNIT-001 {manifest_name} must be a mapping")
        return None
    if data.get("schema_version") != 1:
        errors.append(f"UNIT-002 {manifest_name} schema_version must be 1")

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
    elif set(governance_paths) != GOVERNANCE_PATHS:
        errors.append(
            "UNIT-013 governance must remain contained by .agents/ and the AGENTS.md adapter"
        )

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


def check_guidance_routes(errors: list[str]) -> None:
    for source, targets in GUIDANCE_ROUTES.items():
        path = ROOT / source
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(f"ROUTE-001 cannot read guidance source {source}: {exc}")
            continue
        for target in targets:
            if target not in text:
                errors.append(f"ROUTE-002 {source} must route to {target}")


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
        has_command = "command" in data
        has_phases = "phases" in data
        if has_command == has_phases:
            errors.append(
                f"EXP-003 {path.relative_to(ROOT)} must declare exactly one of command or phases"
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
        if any(relative_path.startswith(prefix) for prefix in TOOL_RUNTIME_PREFIXES):
            errors.append(f"GIT-004 tool runtime state must not be tracked: {relative_path}")
        if path.is_file() and path.stat().st_size > 10 * 1024 * 1024:
            errors.append(f"GIT-003 tracked file exceeds 10 MiB: {relative_path}")


def check_runtime_ignores(errors: list[str]) -> None:
    for prefix in sorted(TOOL_RUNTIME_PREFIXES):
        probe = f"{prefix}repo-check-probe"
        result = subprocess.run(
            ["git", "check-ignore", "--quiet", "--no-index", probe],
            cwd=ROOT,
            check=False,
        )
        if result.returncode != 0:
            errors.append(f"GIT-005 tool runtime path must be ignored: {prefix}")


def check_instruction_overlays(errors: list[str]) -> None:
    path = ROOT / "AGENTS.md"
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append(f"GUIDANCE-001 cannot read AGENTS.md: {exc}")
        return

    stack: list[str] = []
    starts: Counter[str] = Counter()
    for marker in OVERLAY_MARKER.finditer(text):
        name = marker.group("name")
        boundary = marker.group("boundary")
        if boundary == "START":
            starts[name] += 1
            stack.append(name)
            continue

        if not stack:
            errors.append(f"GUIDANCE-002 overlay {name} ends without a start marker")
        elif stack[-1] != name:
            errors.append(f"GUIDANCE-003 overlay {name} closes while {stack[-1]} is still open")
        else:
            stack.pop()

    for name, count in sorted(starts.items()):
        if count > 1:
            errors.append(f"GUIDANCE-004 overlay {name} appears {count} times")
    for name in stack:
        errors.append(f"GUIDANCE-005 overlay {name} has no end marker")


def check_sidecar_boundary(errors: list[str]) -> None:
    for relative_path in sorted(LEGACY_GOVERNANCE_PATHS):
        if (ROOT / relative_path).exists():
            errors.append(f"BOUNDARY-001 governance path escaped sidecar: {relative_path}")

    for path in project_files():
        relative_path = path.relative_to(ROOT)
        relative_name = relative_path.as_posix()
        first_part = relative_path.parts[0]
        is_execution_path = first_part in FUNCTIONAL_EXECUTION_ROOTS
        is_command_file = relative_name in FUNCTIONAL_COMMAND_FILES
        if not (is_execution_path or is_command_file):
            continue
        if path.suffix not in TEXT_SUFFIXES and not is_command_file:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        if ".agents/" in text or ".agents\\" in text:
            errors.append(
                "BOUNDARY-002 functional execution path references governance sidecar: "
                f"{relative_name}"
            )


def main() -> int:
    errors: list[str] = []
    manifest = load_unit_manifest(errors)
    unit_counts: Counter[str] = Counter()
    if manifest is not None:
        unit_counts = check_repository_units(manifest, errors)
    check_yaml(errors)
    check_skills(errors)
    check_guidance_routes(errors)
    check_experiment_specs(errors)
    check_tracked_state(errors)
    check_runtime_ignores(errors)
    check_instruction_overlays(errors)
    check_sidecar_boundary(errors)

    if errors:
        for error in errors:
            print(f"ERROR {error}")
        return 1

    print(
        "OK repository structure, units "
        f"(functional={unit_counts['functional']}, governance={unit_counts['governance']}), "
        "sidecar boundary, runtime isolation, guidance routes and overlays, YAML, skills, "
        "experiment specs, and tracked state"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
