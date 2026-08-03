from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def edit(relative: str, old: str, new: str, *, count: int = 1) -> None:
    path = ROOT / relative
    text = path.read_text(encoding="utf-8")
    actual = text.count(old)
    if actual != count:
        raise RuntimeError(f"{relative}: expected {count}, found {actual}: {old!r}")
    path.write_text(text.replace(old, new), encoding="utf-8")


edit(
    "tests/test_asset_binding.py",
    "    second = experiment_plan.plan_spec(spec_path, tmp_path)\n    assert first == second\n",
    "    second = experiment_plan.plan_spec(spec_path, tmp_path)\n"
    "    assert first[\"protocol\"] == second[\"protocol\"]\n"
    "    assert first[\"execution\"] == second[\"execution\"]\n"
    "    assert first[\"binding\"][\"sha256\"] != second[\"binding\"][\"sha256\"]\n",
)

edit(
    "tests/test_experiment_plan.py",
    "    monkeypatch.setattr(subprocess, \"run\", reject_execution)\n"
    "    rendered = plan_tool.render_plan(spec_path, tmp_path)\n",
    "    monkeypatch.setattr(subprocess, \"run\", reject_execution)\n"
    "    monkeypatch.setattr(\n"
    "        plan_tool.research,\n"
    "        \"git_state\",\n"
    "        lambda _root: {\n"
    "            \"commit\": None,\n"
    "            \"dirty\": False,\n"
    "            \"status\": [],\n"
    "            \"patch_sha256\": \"0\" * 64,\n"
    "        },\n"
    "    )\n"
    "    rendered = plan_tool.render_plan(spec_path, tmp_path)\n",
)

# New result evidence is v2; legacy manifests still produce valid v1 results without identities.
run_state_path = ROOT / "tools/run_state.py"
text = run_state_path.read_text(encoding="utf-8")
start = text.index("def terminal_result(")
end = text.index("\n\ndef write_terminal_result", start)
replacement = '''def manifest_identities(manifest: dict[str, Any]) -> dict[str, str] | None:
    plan = manifest.get("plan")
    if not isinstance(plan, dict):
        return None
    records = [plan.get(layer) for layer in ("protocol", "execution", "binding")]
    if not all(isinstance(record, dict) and isinstance(record.get("sha256"), str) for record in records):
        return None
    return {
        "protocol_sha256": records[0]["sha256"],
        "execution_plan_sha256": records[1]["sha256"],
        "binding_sha256": records[2]["sha256"],
    }


def terminal_result(manifest: dict[str, Any], manifest_sha256: str) -> dict[str, Any]:
    report = completion_report(manifest)
    identities = manifest_identities(manifest)
    result = {
        "result_version": RESULT_VERSION if identities is not None else 1,
        "run_id": manifest["run_id"],
        "state": terminal_state(manifest, report),
        "terminal": True,
        "recorded_at": utc_now(),
        "manifest_sha256": manifest_sha256,
        "return_code": manifest.get("return_code"),
        "termination": manifest.get("termination"),
        "completion": report,
    }
    if identities is not None:
        result["identities"] = identities
    return result
'''
run_state_path.write_text(text[:start] + replacement + text[end:], encoding="utf-8")

edit(
    "tests/test_initialize_project.py",
    '.replace("version: 4", "version: 5")',
    '.replace("version: 5", "version: 6")',
)

compat_path = ROOT / "tests/test_template_compat.py"
text = compat_path.read_text(encoding="utf-8")
text = text.replace("assert compat.migrate(tmp_path, 4) == []", "assert compat.migrate(tmp_path, 5) == []", 1)
text = text.replace(
    'monkeypatch.setattr(compat.initialize_project, "TEMPLATE_VERSION", 5)\n'
    '    assert compat.compatibility_errors(tmp_path) == [\n'
    '        "project template version 4 requires migration to 5"\n'
    '    ]\n'
    '    with pytest.raises(compat.TemplateCompatibilityError, match="missing migration"):\n'
    '        compat.migrate(tmp_path, 5)',
    'monkeypatch.setattr(compat.initialize_project, "TEMPLATE_VERSION", 6)\n'
    '    assert compat.compatibility_errors(tmp_path) == [\n'
    '        "project template version 5 requires migration to 6"\n'
    '    ]\n'
    '    with pytest.raises(compat.TemplateCompatibilityError, match="missing migration"):\n'
    '        compat.migrate(tmp_path, 6)',
    1,
)
old_forward = '''    state["template"]["version"] = 5
    compat.initialize_project.write_text(
        tmp_path / "PROJECT.yaml",
        compat.initialize_project.dump_yaml(state),
    )
    with pytest.raises(compat.TemplateCompatibilityError, match="newer than supported"):
        compat.migrate(tmp_path, 4)
'''
new_forward = '''    state["template"]["version"] = 6
    compat.initialize_project.write_text(
        tmp_path / "PROJECT.yaml",
        compat.initialize_project.dump_yaml(state),
    )
    with pytest.raises(compat.TemplateCompatibilityError, match="newer than supported"):
        compat.migrate(tmp_path, 5)
'''
if text.count(old_forward) != 1:
    raise RuntimeError("unexpected forward-only migration test")
compat_path.write_text(text.replace(old_forward, new_forward), encoding="utf-8")

Path(__file__).unlink()
