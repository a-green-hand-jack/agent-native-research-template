from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
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
            "tools/initialize_project.py",
            "apply",
            "--project-name",
            "Template E2E Project",
            "--distribution-name",
            "template-e2e-project",
            "--package-name",
            "template_e2e_project",
            "--contribution-id",
            "e2e-vertical-slice",
        ],
        root,
    )


def check_functional_residue(root: Path) -> None:
    findings: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if relative.parts and relative.parts[0] in {".agents", "runs"}:
            continue
        if path.suffix not in TEXT_SUFFIXES:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeError:
            continue
        for residue in FUNCTIONAL_RESIDUES:
            if residue in content:
                findings.append(f"{relative.as_posix()}: {residue}")
    if findings:
        raise TemplateVerificationError(
            "initialized functional project retains template residue:\n" + "\n".join(findings)
        )


def verify_latest_run(root: Path) -> None:
    manifests = sorted((root / "runs").glob("*/manifest.json"))
    if not manifests:
        raise TemplateVerificationError("research-run created no run manifest")
    run(
        [
            sys.executable,
            "tools/evidence.py",
            "verify-run",
            manifests[-1].parent.name,
        ],
        root,
    )


def verify_initialized_copy(root: Path) -> None:
    initialize_project(root)
    run(["uv", "sync", "--frozen", "--group", "dev"], root)
    run(["make", "verify"], root)
    run(["make", "research-run"], root)
    verify_latest_run(root)
    check_functional_residue(root)

    shutil.rmtree(root / ".agents")
    (root / "AGENTS.md").unlink()
    shutil.rmtree(root / ".venv")
    run(["uv", "sync", "--frozen", "--group", "dev"], root)
    run(["make", "verify"], root)
    run(["make", "research-run"], root)
    verify_latest_run(root)


def main() -> int:
    try:
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
