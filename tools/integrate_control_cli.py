from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def edit(relative: str, old: str, new: str, *, count: int = 1) -> None:
    path = ROOT / relative
    text = path.read_text(encoding="utf-8")
    actual = text.count(old)
    if actual != count:
        raise RuntimeError(f"{relative}: expected {count} occurrence(s), found {actual}: {old!r}")
    path.write_text(text.replace(old, new), encoding="utf-8")


def append_after(relative: str, marker: str, addition: str) -> None:
    edit(relative, marker, marker + addition)


# Initializer: CLI name is part of one atomic project identity.
edit("tools/initialize_project.py", "TEMPLATE_VERSION = 2", "TEMPLATE_VERSION = 3")
edit(
    "tools/initialize_project.py",
    '    "package_name": "project",\n    "contribution_id": "bootstrap",',
    '    "package_name": "project",\n    "cli_name": "researchctl",\n    "contribution_id": "bootstrap",',
)
append_after(
    "tools/initialize_project.py",
    'CONTRIBUTION_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")\n',
    'CLI_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")\n',
)
edit(
    "tools/initialize_project.py",
    "    package_name: str\n    contribution_id: str",
    "    package_name: str\n    cli_name: str\n    contribution_id: str",
)
edit(
    "tools/initialize_project.py",
    '    if not CONTRIBUTION_PATTERN.fullmatch(identity.contribution_id):\n        raise InitializationError("contribution ID must be a stable lowercase identifier")',
    '    if not CLI_PATTERN.fullmatch(identity.cli_name):\n        raise InitializationError(\n            "CLI name must use lowercase letters, digits, and single hyphens"\n        )\n    if not CONTRIBUTION_PATTERN.fullmatch(identity.contribution_id):\n        raise InitializationError("contribution ID must be a stable lowercase identifier")',
)
edit(
    "tools/initialize_project.py",
    '    if identity.contribution_id == TEMPLATE_STATE["contribution_id"]:\n        raise InitializationError("contribution ID must replace the template value")',
    '    if identity.cli_name == TEMPLATE_STATE["cli_name"]:\n        raise InitializationError("CLI name must replace the template value")\n    if identity.contribution_id == TEMPLATE_STATE["contribution_id"]:\n        raise InitializationError("contribution ID must replace the template value")',
)
edit(
    "tools/initialize_project.py",
    '    for key in TEMPLATE_STATE:\n        if not isinstance(state.get(key), str) or not state[key].strip():\n            errors.append(f"PROJECT.yaml {key} must be a non-empty string")',
    '    template_version = (state.get("template") or {}).get("version", 0)\n    for key in TEMPLATE_STATE:\n        if key == "cli_name" and template_version < 3 and state.get("initialized") is True:\n            continue\n        if not isinstance(state.get(key), str) or not state[key].strip():\n            errors.append(f"PROJECT.yaml {key} must be a non-empty string")',
)
edit(
    "tools/initialize_project.py",
    "    pyproject = replace_required(\n        pyproject,\n        'packages = [\"src/project\"]',\n        f'packages = [\"src/{identity.package_name}\"]',\n        \"pyproject.toml\",\n    )",
    "    pyproject = replace_required(\n        pyproject,\n        'packages = [\"src/project\", \"tools\"]',\n        f'packages = [\"src/{identity.package_name}\", \"tools\"]',\n        \"pyproject.toml\",\n    )\n    pyproject = replace_required(\n        pyproject,\n        'researchctl = \"tools.control_cli:main\"',\n        f'{identity.cli_name} = \"tools.control_cli:main\"',\n        \"pyproject.toml\",\n    )",
)
edit(
    "tools/initialize_project.py",
    '    revision = git_revision(root)\n    readme = read_required(root, "README.md")',
    '    makefile = read_required(root, "Makefile").replace("researchctl", identity.cli_name)\n\n    revision = git_revision(root)\n    readme = read_required(root, "README.md").replace("researchctl", identity.cli_name)',
)
edit(
    "tools/initialize_project.py",
    '        "package_name": identity.package_name,\n        "contribution_id": identity.contribution_id,',
    '        "package_name": identity.package_name,\n        "cli_name": identity.cli_name,\n        "contribution_id": identity.contribution_id,',
)
edit(
    "tools/initialize_project.py",
    '        "pyproject.toml": pyproject,\n        "uv.lock": uv_lock,',
    '        "pyproject.toml": pyproject,\n        "Makefile": makefile,\n        "uv.lock": uv_lock,',
)
edit(
    "tools/initialize_project.py",
    '    identity = ProjectIdentity(\n        project_name=state["project_name"],\n        distribution_name=state["distribution_name"],\n        package_name=state["package_name"],\n        contribution_id=state["contribution_id"],\n    )',
    '    if state["template"]["version"] < TEMPLATE_VERSION:\n        return [\n            f"project template version {state[\'template\'][\'version\']} requires migration "\n            f"to {TEMPLATE_VERSION}"\n        ]\n\n    identity = ProjectIdentity(\n        project_name=state["project_name"],\n        distribution_name=state["distribution_name"],\n        package_name=state["package_name"],\n        cli_name=state["cli_name"],\n        contribution_id=state["contribution_id"],\n    )',
)
edit(
    "tools/initialize_project.py",
    '            f\'packages = ["src/{identity.package_name}"]\',',
    '            f\'packages = ["src/{identity.package_name}", "tools"]\',\n            f\'{identity.cli_name} = "tools.control_cli:main"\',',
)
edit(
    "tools/initialize_project.py",
    '        "tests/smoke/test_project.py",\n        f"src/{identity.package_name}/__init__.py",',
    '        "tests/smoke/test_project.py",\n        f"src/{identity.package_name}/__init__.py",\n        "Makefile",\n        "README.md",',
)
edit(
    "tools/initialize_project.py",
    '    if (root / "src/project").exists():',
    '    template_cli_entry = f\'{TEMPLATE_STATE["cli_name"]} = "tools.control_cli:main"\'\n    if identity.cli_name != TEMPLATE_STATE["cli_name"]:\n        pyproject_content = (root / "pyproject.toml").read_text(encoding="utf-8")\n        if template_cli_entry in pyproject_content:\n            errors.append("initialized project retains template CLI entry")\n    if (root / "src/project").exists():',
)
edit(
    "tools/initialize_project.py",
    '    apply.add_argument("--package-name", required=True)\n    apply.add_argument("--contribution-id", required=True)',
    '    apply.add_argument("--package-name", required=True)\n    apply.add_argument("--cli-name", required=True)\n    apply.add_argument("--contribution-id", required=True)',
)
edit(
    "tools/initialize_project.py",
    '            package_name=args.package_name,\n            contribution_id=args.contribution_id,',
    '            package_name=args.package_name,\n            cli_name=args.cli_name,\n            contribution_id=args.contribution_id,',
)

# Explicit v2 -> v3 downstream migration.
insert = '''\n\ndef migrate_to_v3(root: Path, state: dict[str, Any]) -> list[str]:\n    cli_name = state["distribution_name"]\n    if not initialize_project.CLI_PATTERN.fullmatch(cli_name):\n        raise TemplateCompatibilityError(\n            "distribution_name cannot be used as a CLI name; choose a valid lowercase hyphenated name"\n        )\n    state["cli_name"] = cli_name\n    relative = "pyproject.toml"\n    path = root / relative\n    content = path.read_text(encoding="utf-8")\n    template_entry = 'researchctl = "tools.control_cli:main"'\n    configured_entry = f'{cli_name} = "tools.control_cli:main"'\n    if template_entry in content:\n        content = content.replace(template_entry, configured_entry)\n    elif configured_entry not in content:\n        marker = "[dependency-groups]"\n        if marker not in content:\n            raise TemplateCompatibilityError("pyproject.toml has no dependency-groups section")\n        content = content.replace(marker, f'[project.scripts]\\n{configured_entry}\\n\\n{marker}')\n    initialize_project.write_text(path, content)\n    return [f"write {relative}"]\n'''
edit(
    "tools/template_compat.py",
    "\n\nMIGRATIONS: dict[int, Migration] = {2: migrate_to_v2}",
    insert + "\n\nMIGRATIONS: dict[int, Migration] = {2: migrate_to_v2, 3: migrate_to_v3}",
)

# Initializer tests mirror the real template identity.
edit(
    "tests/test_initialize_project.py",
    '            "package_name: project\\ncontribution_id: bootstrap\\n"',
    '            "package_name: project\\ncli_name: researchctl\\ncontribution_id: bootstrap\\n"',
)
edit("tests/test_initialize_project.py", '            "  version: 2\\n"', '            "  version: 3\\n"')
edit(
    "tests/test_initialize_project.py",
    "            '[tool.hatch.build.targets.wheel]\\npackages = [\"src/project\"]\\n'",
    "            '[project.scripts]\\nresearchctl = \"tools.control_cli:main\"\\n'\n            '[tool.hatch.build.targets.wheel]\\npackages = [\"src/project\", \"tools\"]\\n'",
)
edit(
    "tests/test_initialize_project.py",
    '        package_name="causal_agent_lab",\n        contribution_id="causal-policy",',
    '        package_name="causal_agent_lab",\n        cli_name="causal-lab",\n        contribution_id="causal-policy",',
)
edit(
    "tests/test_initialize_project.py",
    '    assert state["package_name"] == "causal_agent_lab"',
    '    assert state["package_name"] == "causal_agent_lab"\n    assert state["cli_name"] == "causal-lab"\n    assert \'causal-lab = "tools.control_cli:main"\' in (\n        tmp_path / "pyproject.toml"\n    ).read_text(encoding="utf-8")',
)
edit("tests/test_initialize_project.py", '        "version": 2,', '        "version": 3,')
edit(
    "tests/test_initialize_project.py",
    '    assert "Initialized from Agent-Native Research Template v2 at `unknown`" in readme',
    '    assert "Initialized from Agent-Native Research Template v3 at `unknown`" in readme',
)
edit(
    "tests/test_initialize_project.py",
    '.replace("version: 2", "version: 3")',
    '.replace("version: 3", "version: 4")',
)
edit(
    "tests/test_initialize_project.py",
    '        package_name="bad-name",\n        contribution_id="bootstrap",',
    '        package_name="bad-name",\n        cli_name="Bad CLI",\n        contribution_id="bootstrap",',
)

# E2E proves the initialized, renamed, installed CLI before and after sidecar removal.
edit(
    "tools/verify_template_e2e.py",
    '            "--package-name",\n            "template_e2e_project",\n            "--contribution-id",',
    '            "--package-name",\n            "template_e2e_project",\n            "--cli-name",\n            "template-e2e",\n            "--contribution-id",',
)
edit(
    "tools/verify_template_e2e.py",
    '    "contribution: bootstrap",\n)',
    '    "contribution: bootstrap",\n    \'researchctl = "tools.control_cli:main"\',\n)',
)
edit(
    "tools/verify_template_e2e.py",
    '    "pyproject.toml",\n    "src",',
    '    "pyproject.toml",\n    "Makefile",\n    "PROJECT.yaml",\n    "src",',
)
edit(
    "tools/verify_template_e2e.py",
    'def verify_latest_run(root: Path) -> None:',
    'def verify_latest_run(root: Path, cli_name: str = "template-e2e") -> None:',
)
edit(
    "tools/verify_template_e2e.py",
    '            sys.executable,\n            "tools/evidence.py",\n            "verify-run",',
    '            "uv",\n            "run",\n            cli_name,\n            "experiment",\n            "verify-run",',
    count=1,
)
edit(
    "tools/verify_template_e2e.py",
    '    run(["make", "verify"], root)\n    run(["make", "research-run"], root)',
    '    run(["uv", "run", "template-e2e", "--help"], root)\n    run(["make", "verify"], root)\n    run(["make", "research-run"], root)',
    count=1,
)

# Ownership and contract.
edit(
    ".agents/governance/REPO_UNITS.yaml",
    "  - tools/ci_policy.py\n",
    "  - tools/ci_policy.py\n  - tools/control_cli.py\n",
)
edit(
    ".agents/governance/REPO_UNITS.yaml",
    "  - tools/\n" if False else "  - tools/archive.py\n",
    "  - tools/archive.py\n  - tools/__init__.py\n",
)
edit(
    ".agents/governance/CONTRACT.md",
    "## Execution Invariants\n",
    "## Execution Invariants\n\n- The installed project CLI is the only public experiment and archive control surface. Its name is\n  recorded in `PROJECT.yaml` and may be replaced atomically during initialization. Legacy\n  `tools/*.py` entry points are compatibility adapters, not independent implementations.\n",
)

# README and skills use one generic control surface.
for relative in ["README.md", ".agents/skills/run-experiment/SKILL.md", "docs/ARCHIVE_RETIREMENT.md"]:
    path = ROOT / relative
    text = path.read_text(encoding="utf-8")
    text = text.replace("uv run python tools/research.py validate", "uv run researchctl experiment validate")
    text = text.replace("uv run python tools/evidence.py ", "uv run researchctl experiment ")
    text = text.replace("uv run python tools/archive.py ", "uv run researchctl archive ")
    path.write_text(text, encoding="utf-8")

# Compatibility scripts clearly identify the canonical public route.
for relative, group in [
    ("tools/evidence.py", "experiment"),
    ("tools/archive.py", "archive"),
    ("tools/research.py", "experiment validate"),
]:
    path = ROOT / relative
    text = path.read_text(encoding="utf-8")
    marker = 'if __name__ == "__main__":\n'
    if marker not in text:
        raise RuntimeError(f"{relative}: missing main adapter")
    notice = (
        marker
        + '    print("DEPRECATED: use the installed project CLI '
        + group
        + ' command", file=sys.stderr)\n'
    )
    text = text.replace(marker, notice, 1)
    path.write_text(text, encoding="utf-8")

# Template state version and docs.
project = ROOT / "PROJECT.yaml"
text = project.read_text(encoding="utf-8").replace("  version: 2\n", "  version: 3\n")
project.write_text(text, encoding="utf-8")

# Remove this one-shot integration source before the final product commit.
Path(__file__).unlink()
