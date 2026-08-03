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
Path(__file__).unlink()
