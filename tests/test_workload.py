from __future__ import annotations

import sys
from types import ModuleType

from tools import workload


def test_workload_loader_prefers_configured_source_package_over_module_collision(
    tmp_path, monkeypatch
) -> None:
    (tmp_path / "PROJECT.yaml").write_text("package_name: project\n", encoding="utf-8")
    package = tmp_path / "src/project"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "workloads.py").write_text("def main(argv=None):\n    return 41\n", encoding="utf-8")
    collision = ModuleType("project")
    collision.__file__ = str(tmp_path / "tools/project.py")
    monkeypatch.setitem(sys.modules, "project", collision)

    entry = workload.workload_entry(tmp_path)

    assert entry([]) == 41
