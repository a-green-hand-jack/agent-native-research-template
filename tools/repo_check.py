from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = {
    "README.md",
    "AGENTS.md",
    "ANATOMY.md",
    "CONTRACT.md",
    "GUIDE.md",
    "Makefile",
    "pyproject.toml",
    "configs/base.yaml",
    "environments/main.yaml",
    "evals/smoke.yaml",
    "experiments/specs/smoke.yaml",
    ".agents/memory/INDEX.md",
}
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


def load_yaml(path: Path, errors: list[str]) -> object:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        errors.append(f"YAML-001 {path.relative_to(ROOT)}: {exc}")
        return None


def check_required_files(errors: list[str]) -> None:
    for relative_path in sorted(REQUIRED_FILES):
        if not (ROOT / relative_path).is_file():
            errors.append(f"STRUCT-001 missing required file: {relative_path}")


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
    check_required_files(errors)
    check_yaml(errors)
    check_skills(errors)
    check_experiment_specs(errors)
    check_tracked_state(errors)

    if errors:
        for error in errors:
            print(f"ERROR {error}")
        return 1

    print("OK repository structure, YAML, skills, experiment specs, and tracked state")
    return 0


if __name__ == "__main__":
    sys.exit(main())
