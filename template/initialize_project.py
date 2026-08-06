from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.project import (
    STATE_PATH,
    TEMPLATE_NAME,
    TEMPLATE_VERSION,
    ProjectCheckError,
    ProjectIdentity,
    dump_yaml,
    expected_state,
    validate_identity,
    write_text,
)

DOWNSTREAM_README_SECTIONS = {
    "Agent Governance Sidecar",
    "Initialize A Real Project",
    "Repository Lifecycle Skills",
    "Project First",
    "Agent Runtime Compatibility",
    "Human And Agent Routing",
    "Governance Entry Points",
}
DOWNSTREAM_AGENT_FILES = {
    "AGENTS.md": "template/downstream/AGENTS.md",
    ".agents/system/manifest.yaml": "template/downstream/.agents/system/manifest.yaml",
    ".agents/knowledge/README.md": "template/downstream/.agents/knowledge/README.md",
    ".agents/skills/README.md": "template/downstream/.agents/skills/README.md",
    ".agents/memory/README.md": "template/downstream/.agents/memory/README.md",
    ".agents/runtime/.gitignore": "template/downstream/.agents/runtime/.gitignore",
}
DOWNSTREAM_AGENT_DEFAULTS = {
    "AGENTS.md": "# Agent Entry\n\nRun `__CLI_NAME__ project describe --json`, then load only relevant project context under `.agents/`. Use the project CLI for repeatable mechanics. Do not implement project behavior under `.agents/`.\n",
    ".agents/system/manifest.yaml": "schema_version: 1\nproject: __PROJECT_NAME__\ncli: __CLI_NAME__\ncontext_roots: [.agents/knowledge, .agents/skills, .agents/memory]\nruntime: .agents/runtime\n",
    ".agents/knowledge/README.md": "# Project Knowledge\n\nStore project-specific facts here. Keep executable behavior in the functional project and its CLI.\n",
    ".agents/skills/README.md": "# Project Skills\n\nStore project-specific procedures here. Skills should call the project CLI rather than implement project behavior.\n",
    ".agents/memory/README.md": "# Project Memory\n\nStore reviewed project lessons and decisions here. Critical behavior still belongs in code, tests, or formal documentation.\n",
    ".agents/runtime/.gitignore": "*\n!.gitignore\n",
}

InitializationError = ProjectCheckError


def git_revision(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        errors="replace",
    )
    revision = result.stdout.strip()
    return revision if result.returncode == 0 and revision else "unknown"


def replace_required(content: str, old: str, new: str, path: str) -> str:
    if old not in content:
        raise InitializationError(f"expected template text is missing from {path}: {old!r}")
    return content.replace(old, new)


def remove_markdown_sections(content: str, headings: set[str]) -> str:
    kept: list[str] = []
    skipping = False
    for line in content.splitlines(keepends=True):
        if line.startswith("## "):
            skipping = line[3:].strip() in headings
        if not skipping:
            kept.append(line)
    return "".join(kept)


def read_required(root: Path, relative: str) -> str:
    path = root / relative
    if not path.is_file():
        raise InitializationError(f"required template path is missing: {relative}")
    return path.read_text(encoding="utf-8")


def render_downstream_agent_file(content: str, identity: ProjectIdentity) -> str:
    return content.replace("__PROJECT_NAME__", identity.project_name).replace(
        "__CLI_NAME__", identity.cli_name
    )


def build_changes(root: Path, identity: ProjectIdentity) -> dict[str, str]:
    validate_identity(identity)
    state, errors = expected_state(root)
    if errors:
        raise InitializationError("; ".join(errors))
    if state.get("initialized") is True:
        raise InitializationError("project is already initialized")

    pyproject = read_required(root, "pyproject.toml")
    pyproject = replace_required(
        pyproject,
        'name = "agent-native-project"',
        f'name = "{identity.distribution_name}"',
        "pyproject.toml",
    )
    pyproject = replace_required(
        pyproject,
        'description = "Bootstrap package for an agent-native research project"',
        f'description = "{identity.project_name}"',
        "pyproject.toml",
    )
    pyproject = replace_required(
        pyproject,
        'packages = ["src/project", "tools"]',
        f'packages = ["src/{identity.package_name}", "tools"]',
        "pyproject.toml",
    )
    pyproject = replace_required(
        pyproject,
        'researchctl = "tools.control_cli:main"',
        f'{identity.cli_name} = "tools.control_cli:main"',
        "pyproject.toml",
    )

    uv_lock = read_required(root, "uv.lock").replace(
        'name = "agent-native-project"', f'name = "{identity.distribution_name}"'
    )

    contributions = read_required(root, "CONTRIBUTIONS.md")
    old_row = (
        "| bootstrap | Replace with the first real contribution | `src/project/` | "
        "`configs/base.yaml` | `evals/smoke.yaml` | bootstrap |"
    )
    new_row = (
        f"| {identity.contribution_id} | {identity.project_name} initial vertical slice | "
        f"`src/{identity.package_name}/` | `configs/base.yaml` | `evals/smoke.yaml` | active |"
    )
    contributions = replace_required(contributions, old_row, new_row, "CONTRIBUTIONS.md")

    spec = read_required(root, "experiments/specs/smoke.yaml")
    spec = replace_required(
        spec,
        "contribution: bootstrap",
        f"contribution: {identity.contribution_id}",
        "experiments/specs/smoke.yaml",
    )
    spec = replace_required(
        spec,
        "  - researchctl\n  - workload\n",
        f"  - {identity.cli_name}\n  - workload\n",
        "experiments/specs/smoke.yaml",
    )

    source = read_required(root, "src/project/__init__.py")
    source = replace_required(
        source,
        '"""Bootstrap package. Replace this module with the first real project slice."""',
        f'"""{identity.project_name} package."""',
        "src/project/__init__.py",
    )
    source = source.replace("template_status", "project_status")
    source = source.replace("bootstrap smoke test", "initialized smoke test")

    workloads = read_required(root, "src/project/workloads.py")
    workloads = workloads.replace("template_status", "project_status")

    smoke_test = read_required(root, "tests/smoke/test_template.py")
    smoke_test = smoke_test.replace("from project import", f"from {identity.package_name} import")
    smoke_test = smoke_test.replace("template_status", "project_status")
    smoke_test = smoke_test.replace("test_template_vertical_slice", "test_project_vertical_slice")

    makefile = downstream_makefile(read_required(root, "Makefile")).replace(
        "researchctl", identity.cli_name
    )
    workflow = downstream_workflow(read_required(root, ".github/workflows/verify.yml"))

    revision = git_revision(root)
    readme = read_required(root, "README.md").replace("researchctl", identity.cli_name)
    readme = remove_markdown_sections(readme, DOWNSTREAM_README_SECTIONS)
    readme = replace_required(
        readme,
        "# Agent-Native Research Template",
        f"# {identity.project_name}",
        "README.md",
    )
    readme = readme.replace(
        "A project-first GitHub template for ML, DL, RL, agents, benchmarks, environments, and "
        "adjacent\nresearch projects. The functional project remains conventional and runnable on "
        "its own. Optional\nagent governance lives in a non-runtime `.agents/` sidecar.\n",
        f"{identity.project_name} is a project-first research repository with versioned "
        "experiments,\nimmutable run facts, and reviewed evidence.\n",
    )
    readme = readme.replace("## Five-Minute Research Loop", "## Research Loop")
    readme = readme.replace(
        "Create a repository from this template, then run:",
        "From the repository root, run:",
    )
    readme = readme.replace("the bootstrap experiment", "the configured smoke experiment")
    marker = (
        f"\n> Initialized from Agent-Native Research Template v{TEMPLATE_VERSION} at "
        f"`{revision}`. Distribution: `{identity.distribution_name}`; package: "
        f"`{identity.package_name}`.\n"
    )
    first_break = readme.find("\n")
    readme = readme[: first_break + 1] + marker + readme[first_break + 1 :]

    initialized_state = {
        "schema_version": 1,
        "initialized": True,
        "project_name": identity.project_name,
        "distribution_name": identity.distribution_name,
        "package_name": identity.package_name,
        "cli_name": identity.cli_name,
        "contribution_id": identity.contribution_id,
        "template": {
            "name": TEMPLATE_NAME,
            "version": TEMPLATE_VERSION,
            "initialized_from_commit": revision,
            "reviewed_template_commit": revision,
            "applied_migrations": [],
        },
    }
    changes = {
        STATE_PATH: dump_yaml(initialized_state),
        "pyproject.toml": pyproject,
        "Makefile": makefile,
        ".github/workflows/verify.yml": workflow,
        "uv.lock": uv_lock,
        "CONTRIBUTIONS.md": contributions,
        "experiments/specs/smoke.yaml": spec,
        f"src/{identity.package_name}/__init__.py": source,
        f"src/{identity.package_name}/workloads.py": workloads,
        "tests/smoke/test_project.py": smoke_test,
        "README.md": readme,
    }
    for target, source_path in DOWNSTREAM_AGENT_FILES.items():
        source = root / source_path
        content = (
            source.read_text(encoding="utf-8")
            if source.is_file()
            else DOWNSTREAM_AGENT_DEFAULTS[target]
        )
        changes[target] = render_downstream_agent_file(content, identity)
    return changes


def downstream_makefile(content: str) -> str:
    lines = content.splitlines(keepends=True)
    rendered: list[str] = []
    skipping = False
    removed_targets = {"template-compat", "template-test", "template-e2e"}
    for line in lines:
        if line.startswith(".PHONY:"):
            tokens = [token for token in line.split() if token not in removed_targets]
            line = " ".join(tokens) + "\n"
        if any(line.startswith(f"{target}:") for target in removed_targets):
            skipping = True
            continue
        if skipping and line.strip() == "":
            skipping = False
            continue
        if skipping:
            continue
        for target in removed_targets:
            line = line.replace(f" {target}", "")
        rendered.append(line)
    return "".join(rendered)


def downstream_workflow(content: str) -> str:
    block = (
        "      - name: Initialize and verify a real project copy\n"
        "        run: make template-e2e\n\n"
    )
    return replace_required(content, block, "", ".github/workflows/verify.yml")


def apply_changes(root: Path, identity: ProjectIdentity, *, dry_run: bool = False) -> list[str]:
    changes = build_changes(root, identity)
    removed = [
        "AGENTS.md",
        ".agents/",
        "src/project/__init__.py",
        "src/project/workloads.py",
        "tests/smoke/test_template.py",
        "template/",
    ]
    targets = set(changes)
    optional_source_paths = {"AGENTS.md", ".agents/"}
    for relative in removed:
        path = root / relative.rstrip("/")
        if relative in optional_source_paths:
            continue
        if relative not in targets and not path.exists():
            raise InitializationError(f"required source path disappeared before apply: {relative}")
    planned = [f"remove {path}" for path in removed] + [f"write {path}" for path in sorted(changes)]
    if dry_run:
        return planned
    for relative in removed:
        path = root / relative.rstrip("/")
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
                continue
            path.unlink()
            parent = path.parent
            if parent != root and not any(parent.iterdir()):
                parent.rmdir()
    for relative, content in changes.items():
        write_text(root / relative, content)
    return planned


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Initialize a repository created from this template."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    apply = subparsers.add_parser("apply", help="replace bootstrap project identity")
    apply.add_argument("--project-name", required=True)
    apply.add_argument("--distribution-name", required=True)
    apply.add_argument("--package-name", required=True)
    apply.add_argument("--cli-name", required=True)
    apply.add_argument("--contribution-id", required=True)
    apply.add_argument("--dry-run", action="store_true")

    return parser


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    args = build_parser().parse_args(argv)
    try:
        identity = ProjectIdentity(
            project_name=args.project_name,
            distribution_name=args.distribution_name,
            package_name=args.package_name,
            cli_name=args.cli_name,
            contribution_id=args.contribution_id,
        )
        planned = apply_changes(root, identity, dry_run=args.dry_run)
        for item in planned:
            print(item)
        return 0
    except (InitializationError, OSError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
