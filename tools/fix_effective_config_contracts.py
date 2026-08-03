from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

schema_path = ROOT / "schemas/run-manifest.schema.json"
schema = json.loads(schema_path.read_text(encoding="utf-8"))
path_hash = schema["$defs"]["path_hash"]
path_hash["properties"]["resolved"] = {"type": "object"}
schema_path.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")

repo_check = ROOT / ".agents/governance/tools/repo_check.py"
text = repo_check.read_text(encoding="utf-8")
old_fields = '''REQUIRED_EXPERIMENT_FIELDS = {
    "id",
    "contribution",
    "config",
    "environment",
    "executor",
    "evaluation",
    "command",
}'''
new_fields = '''REQUIRED_EXPERIMENT_FIELDS = {
    "id",
    "contribution",
    "config",
    "environment",
    "executor",
    "evaluation",
}'''
if text.count(old_fields) != 1:
    raise RuntimeError("governance experiment field set changed")
text = text.replace(old_fields, new_fields)
old_check = '''        missing = REQUIRED_EXPERIMENT_FIELDS - data.keys()
        if missing:
            errors.append(
                f"EXP-002 {path.relative_to(ROOT)} missing fields: {', '.join(sorted(missing))}"
            )'''
new_check = '''        missing = REQUIRED_EXPERIMENT_FIELDS - data.keys()
        if missing:
            errors.append(
                f"EXP-002 {path.relative_to(ROOT)} missing fields: {', '.join(sorted(missing))}"
            )
        has_command = "command" in data
        has_phases = "phases" in data
        if has_command == has_phases:
            errors.append(
                f"EXP-003 {path.relative_to(ROOT)} must declare exactly one of command or phases"
            )'''
if text.count(old_check) != 1:
    raise RuntimeError("governance experiment validation block changed")
repo_check.write_text(text.replace(old_check, new_check), encoding="utf-8")

Path(__file__).unlink()
