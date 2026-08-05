from __future__ import annotations

import importlib
import sys
from pathlib import Path

try:
    from . import project
except ImportError:  # compatibility for direct script execution
    import project


class WorkloadError(ValueError):
    """Raised when the configured project workload surface is unavailable."""


def workload_entry(root: Path):
    state = project.load_yaml(root / project.STATE_PATH)
    package_name = state.get("package_name")
    if not isinstance(package_name, str) or not project.PACKAGE_PATTERN.fullmatch(package_name):
        raise WorkloadError("PROJECT.yaml package_name must be a lowercase Python identifier")
    source_root = root / "src"
    if not source_root.is_dir():
        raise WorkloadError("project workload source root is missing: src")
    source_text = str(source_root.resolve())
    sys.path[:] = [entry for entry in sys.path if entry != source_text]
    sys.path.insert(0, source_text)
    expected_package = (source_root / package_name).resolve()
    loaded = sys.modules.get(package_name)
    loaded_file = getattr(loaded, "__file__", None)
    if loaded is not None and (
        loaded_file is None or expected_package not in Path(loaded_file).resolve().parents
    ):
        for module_name in tuple(sys.modules):
            if module_name == package_name or module_name.startswith(f"{package_name}."):
                del sys.modules[module_name]
    importlib.invalidate_caches()
    try:
        module = importlib.import_module(f"{package_name}.workloads")
    except (ImportError, ModuleNotFoundError) as exc:
        raise WorkloadError(
            f"project workload module is unavailable: {package_name}.workloads"
        ) from exc
    entry = getattr(module, "main", None)
    if not callable(entry):
        raise WorkloadError(f"{package_name}.workloads must expose callable main(argv)")
    return entry


def main(argv: list[str] | None = None, root: Path | None = None) -> int:
    project_root = (root or Path.cwd()).resolve()
    try:
        return int(workload_entry(project_root)(list(argv or [])))
    except (OSError, project.ProjectCheckError, WorkloadError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2
