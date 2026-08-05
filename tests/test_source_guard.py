from __future__ import annotations

from tools import source_guard


def test_source_guard_reports_created_changed_and_removed_files(tmp_path) -> None:
    source = tmp_path / "src/model.py"
    source.parent.mkdir(parents=True)
    source.write_text("original\n", encoding="utf-8")
    before = source_guard.protected_snapshot(tmp_path)

    source.write_text("changed\n", encoding="utf-8")
    created = tmp_path / "configs/new.yaml"
    created.parent.mkdir(parents=True)
    created.write_text("value: 1\n", encoding="utf-8")
    removed = tmp_path / "tests/removed.py"
    removed.parent.mkdir(parents=True)
    removed.write_text("", encoding="utf-8")
    with_removed = source_guard.protected_snapshot(tmp_path)
    removed.unlink()
    after = source_guard.protected_snapshot(tmp_path)

    assert source_guard.mutation_errors(before, with_removed) == [
        "protected project file created: configs/new.yaml",
        "protected project file changed: src/model.py",
        "protected project file created: tests/removed.py",
    ]
    assert source_guard.mutation_errors(with_removed, after) == [
        "protected project file removed: tests/removed.py"
    ]


def test_source_guard_allows_preexisting_unchanged_project_state(tmp_path) -> None:
    source = tmp_path / "src/model.py"
    source.parent.mkdir(parents=True)
    source.write_text("already dirty\n", encoding="utf-8")
    before = source_guard.protected_snapshot(tmp_path)

    assert source_guard.mutation_errors(before, source_guard.protected_snapshot(tmp_path)) == []
