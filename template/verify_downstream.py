from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IGNORED_COPY_NAMES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "runs",
}
FUNCTIONAL_RESIDUES = (
    "agent-native-project",
    "src/project",
    "from project import",
    "contribution: bootstrap",
    'researchctl = "tools.control_cli:main"',
    "# Agent-Native Research Template",
    "## Initialize A Real Project",
    "## Repository Lifecycle Skills",
    "the bootstrap experiment",
)
RESIDUE_SURFACES = (
    "CONTRIBUTIONS.md",
    "README.md",
    "configs",
    "environments",
    "evals",
    "experiments",
    "infra",
    "pyproject.toml",
    "Makefile",
    "PROJECT.yaml",
    "src",
    "uv.lock",
)
TEXT_SUFFIXES = {
    "",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}


class TemplateVerificationError(RuntimeError):
    """Raised when the real initialized template fails an end-to-end check."""


def copy_ignore(_: str, names: list[str]) -> set[str]:
    return {name for name in names if name in IGNORED_COPY_NAMES}


def run(command: list[str], root: Path) -> str:
    environment = os.environ.copy()
    result = subprocess.run(
        command,
        cwd=root,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        errors="replace",
    )
    output = result.stdout + result.stderr
    if result.returncode != 0:
        rendered = " ".join(command)
        raise TemplateVerificationError(
            f"command failed with exit code {result.returncode}: {rendered}\n{output}"
        )
    return output


def initialize_project(root: Path) -> None:
    run(
        [
            sys.executable,
            "template/initialize_project.py",
            "apply",
            "--project-name",
            "Template E2E Project",
            "--distribution-name",
            "template-e2e-project",
            "--package-name",
            "template_e2e_project",
            "--cli-name",
            "template-e2e",
            "--contribution-id",
            "e2e-vertical-slice",
        ],
        root,
    )


def surface_files(root: Path) -> list[Path]:
    selected: list[Path] = []
    for relative in RESIDUE_SURFACES:
        path = root / relative
        if path.is_file():
            selected.append(path)
        elif path.is_dir():
            selected.extend(candidate for candidate in path.rglob("*") if candidate.is_file())
    return sorted(set(selected))


def check_functional_residue(root: Path) -> None:
    findings: list[str] = []
    for path in surface_files(root):
        if path.suffix not in TEXT_SUFFIXES:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeError:
            continue
        for residue in FUNCTIONAL_RESIDUES:
            if residue in content:
                relative = path.relative_to(root).as_posix()
                findings.append(f"{relative}: {residue}")
    if findings:
        raise TemplateVerificationError(
            "initialized functional project retains template residue:\n" + "\n".join(findings)
        )


def verify_latest_run(root: Path, cli_name: str = "template-e2e") -> None:
    manifests = sorted((root / "runs").glob("*/manifest.json"))
    if not manifests:
        raise TemplateVerificationError("research-run created no run manifest")
    run(
        [
            "uv",
            "run",
            cli_name,
            "experiment",
            "verify-run",
            manifests[-1].parent.name,
        ],
        root,
    )


def check_downstream_projection(root: Path) -> None:
    absent = (
        "template",
        "tools/initialize_project.py",
        "tools/verify_template_e2e.py",
    )
    leftovers = [relative for relative in absent if (root / relative).exists()]
    if leftovers:
        raise TemplateVerificationError(
            "initialized project retains template-only paths: " + ", ".join(leftovers)
        )

    for relative in ("Makefile", ".github/workflows/verify.yml"):
        content = (root / relative).read_text(encoding="utf-8")
        residues = ("template-e2e:", "template-test:", "make template-e2e")
        if any(residue in content for residue in residues):
            raise TemplateVerificationError(
                f"initialized project retains template target in {relative}"
            )

    configuration = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    packages = configuration["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"]
    if packages != ["src/template_e2e_project", "tools"]:
        raise TemplateVerificationError(
            f"initialized wheel has unexpected retained packages: {packages!r}"
        )


def check_runtime_only_paths_are_untracked() -> None:
    tracked = run(["git", "ls-files", ".codex", ".codex/**"], ROOT).strip()
    if tracked:
        raise TemplateVerificationError(f"runtime-only .codex path is tracked:\n{tracked}")


def verify_initialized_copy(root: Path) -> None:
    initialize_project(root)
    check_downstream_projection(root)
    run(["uv", "sync", "--frozen", "--group", "dev"], root)
    run(["uv", "run", "template-e2e", "--help"], root)
    run(["uv", "run", "template-e2e", "project", "check"], root)
    run(["uv", "run", "template-e2e", "archive", "--help"], root)
    run(["uv", "run", "template-e2e", "release", "--help"], root)
    run(["uv", "run", "template-e2e", "template", "--help"], root)
    run(["make", "verify"], root)
    run(["make", "research-run"], root)
    verify_latest_run(root)
    check_functional_residue(root)

    shutil.rmtree(root / ".agents")
    (root / "AGENTS.md").unlink()
    shutil.rmtree(root / ".venv")
    run(["uv", "sync", "--frozen", "--group", "dev"], root)
    run(["uv", "run", "template-e2e", "--help"], root)
    run(["uv", "run", "template-e2e", "project", "check"], root)
    run(["uv", "run", "template-e2e", "archive", "--help"], root)
    run(["uv", "run", "template-e2e", "release", "--help"], root)
    run(["make", "verify"], root)
    run(["make", "research-run"], root)
    verify_latest_run(root)


def main() -> int:
    try:
        check_runtime_only_paths_are_untracked()
        with tempfile.TemporaryDirectory(prefix="agent-native-template-e2e-") as temporary:
            root = Path(temporary) / "project"
            shutil.copytree(ROOT, root, ignore=copy_ignore)
            verify_initialized_copy(root)
    except (OSError, TemplateVerificationError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1
    print("OK real template initialization, research execution, and sidecar independence")
    return 0


if __name__ == "__main__":
    sys.exit(main())
