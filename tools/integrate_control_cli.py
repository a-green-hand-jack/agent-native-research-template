from __future__ import annotations

import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "tools/integrate_control_cli_wrapper.py"

# This marker is intentionally rewritten by the already-running scoped workflow snapshot.
WORKFLOW_PATCH_MARKER = """    count=1,
)

# Ownership and contract."""

text = WRAPPER.read_text(encoding="utf-8")
migration_start = text.index("new_migration = '''")
migration_end = text.index("'''\nedit(\"tools/template_compat.py\"", migration_start)
migration_source = text[migration_start:migration_end]
migration_source = migration_source.replace("\\n", "\\\\n")
text = text[:migration_start] + migration_source + text[migration_end:]

old = 'edit("tools/template_compat.py", old_migration, new_migration)'
replacement = '''path = ROOT / "tools/template_compat.py"
text = path.read_text(encoding="utf-8")
start = text.index("def migrate_to_v3(")
end = text.index("\\n\\nMIGRATIONS:", start)
path.write_text(text[:start] + new_migration + text[end:], encoding="utf-8")'''
if text.count(old) != 1:
    raise RuntimeError("unexpected migration replacement call in integration wrapper")
WRAPPER.write_text(text.replace(old, replacement), encoding="utf-8")

runpy.run_path(str(WRAPPER))

# Move dev-dependency removal before the new runtime dependency block is written.
compat_path = ROOT / "tools/template_compat.py"
compat_text = compat_path.read_text(encoding="utf-8")
old_order = '''    if "dependencies = []" in content:
        content = content.replace("dependencies = []", runtime_dependencies)
    content = content.replace('    "jsonschema>=4.23",\\n', "")
    content = content.replace('    "pyyaml>=6.0",\\n', "")'''
new_order = '''    content = content.replace('    "jsonschema>=4.23",\\n', "")
    content = content.replace('    "pyyaml>=6.0",\\n', "")
    if "dependencies = []" in content:
        content = content.replace("dependencies = []", runtime_dependencies)'''
if compat_text.count(old_order) != 1:
    raise RuntimeError("unexpected generated runtime dependency migration order")
compat_path.write_text(compat_text.replace(old_order, new_order), encoding="utf-8")

# Exercise migration 2 against the version-2 contract, independently of the v3 migration test.
test_path = ROOT / "tests/test_template_compat.py"
test_text = test_path.read_text(encoding="utf-8")
start = test_text.index("def test_version_2_migration_adds_smoke_input_identity(")
end = test_text.index("\n\ndef test_version_3_migration_installs_configured_control_surface", start)
section = test_text[start:end]
section = section.replace(
    "def test_version_2_migration_adds_smoke_input_identity(tmp_path: Path) -> None:",
    "def test_version_2_migration_adds_smoke_input_identity(\n"
    "    tmp_path: Path, monkeypatch: pytest.MonkeyPatch\n"
    ") -> None:",
)
section = section.replace(
    "    initialized_project(tmp_path)\n",
    "    initialized_project(tmp_path)\n"
    "    monkeypatch.setattr(compat.initialize_project, \"TEMPLATE_VERSION\", 2)\n",
    1,
)
section = section.replace(
    '"project template version 1 requires migration to 3"',
    '"project template version 1 requires migration to 2"',
)
section = section.replace(
    "    assert compat.compatibility_errors(tmp_path) == [\n"
    "        \"project template version 2 requires migration to 3\"\n"
    "    ]",
    "    assert compat.compatibility_errors(tmp_path) == []",
)
test_path.write_text(test_text[:start] + section + test_text[end:], encoding="utf-8")

Path(__file__).unlink()
