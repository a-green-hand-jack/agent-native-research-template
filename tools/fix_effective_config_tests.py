from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise RuntimeError(f"{path}: expected one occurrence, found {text.count(old)}: {old!r}")
    path.write_text(text.replace(old, new), encoding="utf-8")


initializer_test = ROOT / "tests/test_initialize_project.py"
replace_once(
    initializer_test,
    '.replace("version: 3", "version: 4")',
    '.replace("version: 4", "version: 5")',
)

phase_test = ROOT / "tests/test_phase_recovery_evidence.py"
replace_once(
    phase_test,
    '    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))\n    spec["phases"] = [',
    '    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))\n'
    '    spec.pop("command", None)\n'
    '    spec["phases"] = [',
)

compat_test = ROOT / "tests/test_template_compat.py"
text = compat_test.read_text(encoding="utf-8")
text = text.replace(
    "    assert compat.migrate(tmp_path, 3) == []\n",
    "    assert compat.migrate(tmp_path, 4) == []\n",
    1,
)
old_v3 = '''def test_version_3_migration_installs_configured_control_surface(tmp_path: Path) -> None:
    initialized_project(tmp_path)
'''
new_v3 = '''def test_version_3_migration_installs_configured_control_surface(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(compat.initialize_project, "TEMPLATE_VERSION", 3)
    initialized_project(tmp_path)
'''
if text.count(old_v3) != 1:
    raise RuntimeError("unexpected version-3 migration test signature")
text = text.replace(old_v3, new_v3)
text = text.replace(
    '    monkeypatch.setattr(compat.initialize_project, "TEMPLATE_VERSION", 4)\n'
    '    assert compat.compatibility_errors(tmp_path) == [\n'
    '        "project template version 3 requires migration to 4"\n'
    '    ]\n'
    '    with pytest.raises(compat.TemplateCompatibilityError, match="missing migration"):\n'
    '        compat.migrate(tmp_path, 4)',
    '    monkeypatch.setattr(compat.initialize_project, "TEMPLATE_VERSION", 5)\n'
    '    assert compat.compatibility_errors(tmp_path) == [\n'
    '        "project template version 4 requires migration to 5"\n'
    '    ]\n'
    '    with pytest.raises(compat.TemplateCompatibilityError, match="missing migration"):\n'
    '        compat.migrate(tmp_path, 5)',
    1,
)
old_forward = '''    state["template"]["version"] = 4
    compat.initialize_project.write_text(
        tmp_path / "PROJECT.yaml",
        compat.initialize_project.dump_yaml(state),
    )
    with pytest.raises(compat.TemplateCompatibilityError, match="newer than supported"):
        compat.migrate(tmp_path, 3)
'''
new_forward = '''    state["template"]["version"] = 5
    compat.initialize_project.write_text(
        tmp_path / "PROJECT.yaml",
        compat.initialize_project.dump_yaml(state),
    )
    with pytest.raises(compat.TemplateCompatibilityError, match="newer than supported"):
        compat.migrate(tmp_path, 4)
'''
if text.count(old_forward) != 1:
    raise RuntimeError("unexpected forward-only migration test")
text = text.replace(old_forward, new_forward)
text = text.replace(
    "        compat.migrate(tmp_path, 3)\n",
    "        compat.migrate(tmp_path, 4)\n",
    1,
)
compat_test.write_text(text, encoding="utf-8")

Path(__file__).unlink()
