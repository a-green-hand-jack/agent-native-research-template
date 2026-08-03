from __future__ import annotations

import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "tools/integrate_control_cli_base.py"

# This marker is intentionally rewritten by the already-running scoped workflow snapshot.
WORKFLOW_PATCH_MARKER = """    count=1,
)

# Ownership and contract."""


def edit(relative: str, old: str, new: str, *, count: int = 1) -> None:
    path = ROOT / relative
    text = path.read_text(encoding="utf-8")
    actual = text.count(old)
    if actual != count:
        raise RuntimeError(f"{relative}: expected {count} occurrence(s), found {actual}: {old!r}")
    path.write_text(text.replace(old, new), encoding="utf-8")


# The preserved base script expects two identical E2E execution blocks.
base_text = BASE.read_text(encoding="utf-8")
marker = "    count=1,\n)\n\n# Ownership and contract."
if base_text.count(marker) != 1:
    raise RuntimeError("unexpected E2E marker in preserved integration base")
BASE.write_text(base_text.replace(marker, "    count=2,\n)\n\n# Ownership and contract."), encoding="utf-8")

runpy.run_path(str(BASE))

# The reduced initializer fixture must include every identity-owned surface.
edit(
    "tests/test_initialize_project.py",
    "        \"uv.lock\": '[[package]]\\nname = \"agent-native-project\"\\n',\n        \"CONTRIBUTIONS.md\": (",
    "        \"uv.lock\": '[[package]]\\nname = \"agent-native-project\"\\n',\n"
    "        \"Makefile\": (\n"
    "            \".PHONY: research-validate research-run verify\\n\"\n"
    "            \"research-validate:\\n\\tuv run researchctl experiment validate\\n\"\n"
    "            \"research-run:\\n\\tuv run researchctl experiment run experiments/specs/smoke.yaml\\n\"\n"
    "            \"verify: research-validate\\n\"\n"
    "        ),\n"
    "        \"CONTRIBUTIONS.md\": (",
)

# Avoid a lint-only ambiguity in the generated compatibility message.
edit(
    "tools/initialize_project.py",
    "        return [\n"
    "            f\"project template version {state['template']['version']} requires migration \"\n"
    "            f\"to {TEMPLATE_VERSION}\"\n"
    "        ]",
    "        return [\n"
    "            f\"project template version {state['template']['version']} requires migration to {TEMPLATE_VERSION}\"\n"
    "        ]",
)

old_migration = '''def migrate_to_v3(root: Path, state: dict[str, Any]) -> list[str]:
    cli_name = state["distribution_name"]
    if not initialize_project.CLI_PATTERN.fullmatch(cli_name):
        raise TemplateCompatibilityError(
            "distribution_name cannot be used as a CLI name; choose a valid lowercase hyphenated name"
        )
    state["cli_name"] = cli_name
    relative = "pyproject.toml"
    path = root / relative
    content = path.read_text(encoding="utf-8")
    template_entry = 'researchctl = "tools.control_cli:main"'
    configured_entry = f'{cli_name} = "tools.control_cli:main"'
    if template_entry in content:
        content = content.replace(template_entry, configured_entry)
    elif configured_entry not in content:
        marker = "[dependency-groups]"
        if marker not in content:
            raise TemplateCompatibilityError("pyproject.toml has no dependency-groups section")
        content = content.replace(marker, f'[project.scripts]\n{configured_entry}\n\n{marker}')
    initialize_project.write_text(path, content)
    return [f"write {relative}"]
'''
new_migration = '''def migrate_to_v3(root: Path, state: dict[str, Any]) -> list[str]:
    cli_name = state["distribution_name"]
    if not initialize_project.CLI_PATTERN.fullmatch(cli_name):
        raise TemplateCompatibilityError(
            "distribution_name cannot be used as a CLI name; choose a valid lowercase hyphenated name"
        )
    state["cli_name"] = cli_name
    changes: list[str] = []

    pyproject_path = root / "pyproject.toml"
    content = pyproject_path.read_text(encoding="utf-8")
    runtime_dependencies = (
        'dependencies = [\n'
        '    "jsonschema>=4.23",\n'
        '    "pyyaml>=6.0",\n'
        ']'
    )
    if "dependencies = []" in content:
        content = content.replace("dependencies = []", runtime_dependencies)
    content = content.replace('    "jsonschema>=4.23",\n', "")
    content = content.replace('    "pyyaml>=6.0",\n', "")
    configured_entry = f'{cli_name} = "tools.control_cli:main"'
    template_entry = 'researchctl = "tools.control_cli:main"'
    if template_entry in content:
        content = content.replace(template_entry, configured_entry)
    elif configured_entry not in content:
        marker = "[dependency-groups]"
        if marker not in content:
            raise TemplateCompatibilityError("pyproject.toml has no dependency-groups section")
        content = content.replace(marker, f"[project.scripts]\n{configured_entry}\n\n{marker}")
    package_marker = f'packages = ["src/{state["package_name"]}"]'
    package_replacement = f'packages = ["src/{state["package_name"]}", "tools"]'
    if package_marker in content:
        content = content.replace(package_marker, package_replacement)
    elif package_replacement not in content:
        raise TemplateCompatibilityError("pyproject.toml does not expose the initialized package")
    initialize_project.write_text(pyproject_path, content)
    changes.append("write pyproject.toml")

    makefile_path = root / "Makefile"
    if makefile_path.is_file():
        makefile = makefile_path.read_text(encoding="utf-8")
        makefile = makefile.replace(
            "uv run python tools/research.py validate\n\tuv run python tools/evidence.py validate",
            f"uv run {cli_name} experiment validate",
        )
        makefile = makefile.replace(
            "uv run python tools/evidence.py run experiments/specs/smoke.yaml",
            f"uv run {cli_name} experiment run experiments/specs/smoke.yaml",
        )
        if "control-cli:" not in makefile:
            makefile = makefile.replace(
                "research-validate:\n",
                f"control-cli:\n\tuv run {cli_name} --help >/dev/null\n\nresearch-validate:\n",
            )
            makefile = makefile.replace("verify: ", "verify: control-cli ")
        initialize_project.write_text(makefile_path, makefile)
        changes.append("write Makefile")

    readme_path = root / "README.md"
    if readme_path.is_file():
        readme = readme_path.read_text(encoding="utf-8")
        readme = readme.replace("uv run python tools/research.py validate", f"uv run {cli_name} experiment validate")
        readme = readme.replace("uv run python tools/evidence.py ", f"uv run {cli_name} experiment ")
        readme = readme.replace("uv run python tools/archive.py ", f"uv run {cli_name} archive ")
        initialize_project.write_text(readme_path, readme)
        changes.append("write README.md")
    return changes
'''
edit("tools/template_compat.py", old_migration, new_migration)

# Update compatibility tests to exercise the full v1 -> v2 -> v3 chain.
edit(
    "tests/test_template_compat.py",
    "    assert compat.migrate(tmp_path, 2) == []",
    "    assert compat.migrate(tmp_path, 3) == []",
)
edit(
    "tests/test_template_compat.py",
    '        "project template version 1 requires migration to 2"',
    '        "project template version 1 requires migration to 3"',
)
edit(
    "tests/test_template_compat.py",
    "    assert compat.compatibility_errors(tmp_path) == []\n\n\ndef test_check_reports_missing_future_migration(",
    "    assert compat.compatibility_errors(tmp_path) == [\n"
    "        \"project template version 2 requires migration to 3\"\n"
    "    ]\n\n\n"
    "def test_version_3_migration_installs_configured_control_surface(tmp_path: Path) -> None:\n"
    "    initialized_project(tmp_path)\n"
    "    state = compat.initialize_project.load_yaml(tmp_path / \"PROJECT.yaml\")\n"
    "    state[\"template\"][\"version\"] = 2\n"
    "    state[\"template\"][\"applied_migrations\"] = [2]\n"
    "    state.pop(\"cli_name\")\n"
    "    compat.initialize_project.write_text(\n"
    "        tmp_path / \"PROJECT.yaml\", compat.initialize_project.dump_yaml(state)\n"
    "    )\n"
    "    (tmp_path / \"pyproject.toml\").write_text(\n"
    "        '[project]\\nname = \"causal-agent-lab\"\\nversion = \"0.1.0\"\\n'\n"
    "        'description = \"Causal Agent Lab\"\\ndependencies = []\\n\\n'\n"
    "        '[dependency-groups]\\ndev = [\\n'\n"
    "        '    \"jsonschema>=4.23\",\\n    \"pyyaml>=6.0\",\\n    \"pytest>=8.0\",\\n]\\n\\n'\n"
    "        '[tool.hatch.build.targets.wheel]\\npackages = [\"src/causal_agent_lab\"]\\n',\n"
    "        encoding=\"utf-8\",\n"
    "    )\n"
    "    (tmp_path / \"Makefile\").write_text(\n"
    "        '.PHONY: research-validate research-run verify\\n'\n"
    "        'research-validate:\\n\\tuv run python tools/research.py validate\\n'\n"
    "        '\\tuv run python tools/evidence.py validate\\n'\n"
    "        'research-run:\\n\\tuv run python tools/evidence.py run experiments/specs/smoke.yaml\\n'\n"
    "        'verify: research-validate\\n',\n"
    "        encoding=\"utf-8\",\n"
    "    )\n"
    "    changes = compat.migrate(tmp_path, 3)\n"
    "    assert changes == [\"write pyproject.toml\", \"write Makefile\", \"write README.md\"]\n"
    "    migrated = compat.initialize_project.load_yaml(tmp_path / \"PROJECT.yaml\")\n"
    "    assert migrated[\"cli_name\"] == \"causal-agent-lab\"\n"
    "    assert migrated[\"template\"][\"version\"] == 3\n"
    "    assert migrated[\"template\"][\"applied_migrations\"] == [2, 3]\n"
    "    pyproject = (tmp_path / \"pyproject.toml\").read_text(encoding=\"utf-8\")\n"
    "    assert 'causal-agent-lab = \"tools.control_cli:main\"' in pyproject\n"
    "    assert 'packages = [\"src/causal_agent_lab\", \"tools\"]' in pyproject\n"
    "    assert '\"jsonschema>=4.23\"' in pyproject.split(\"[dependency-groups]\", 1)[0]\n"
    "    makefile = (tmp_path / \"Makefile\").read_text(encoding=\"utf-8\")\n"
    "    assert \"uv run causal-agent-lab experiment validate\" in makefile\n"
    "    assert \"control-cli:\" in makefile\n\n\n"
    "def test_check_reports_missing_future_migration(",
)
edit(
    "tests/test_template_compat.py",
    '    monkeypatch.setattr(compat.initialize_project, "TEMPLATE_VERSION", 3)\n    assert compat.compatibility_errors(tmp_path) == [\n        "project template version 2 requires migration to 3"\n    ]\n    with pytest.raises(compat.TemplateCompatibilityError, match="missing migration"):\n        compat.migrate(tmp_path, 3)',
    '    monkeypatch.setattr(compat.initialize_project, "TEMPLATE_VERSION", 4)\n    assert compat.compatibility_errors(tmp_path) == [\n        "project template version 3 requires migration to 4"\n    ]\n    with pytest.raises(compat.TemplateCompatibilityError, match="missing migration"):\n        compat.migrate(tmp_path, 4)',
)
edit(
    "tests/test_template_compat.py",
    '    state["template"]["version"] = 3',
    '    state["template"]["version"] = 4',
)
edit(
    "tests/test_template_compat.py",
    "        compat.migrate(tmp_path, 2)\n\n\ndef test_uninitialized_template_cannot_run_downstream_migrations",
    "        compat.migrate(tmp_path, 3)\n\n\ndef test_uninitialized_template_cannot_run_downstream_migrations",
)
edit(
    "tests/test_template_compat.py",
    "        compat.migrate(tmp_path, 2)\n",
    "        compat.migrate(tmp_path, 3)\n",
    count=1,
)

# Remove both one-shot integration layers after successful execution.
Path(__file__).unlink()
