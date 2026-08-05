from __future__ import annotations

import os
import subprocess
import tomllib
from pathlib import Path


def test_uv_cache_is_project_local_and_ignored(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    read_only_home = tmp_path / "home"
    read_only_home.mkdir()
    read_only_home.chmod(0o555)

    environment = os.environ.copy()
    environment["HOME"] = str(read_only_home)
    for name in ("UV_CACHE_DIR", "UV_CONFIG_FILE", "UV_NO_CONFIG", "XDG_CACHE_HOME"):
        environment.pop(name, None)

    result = subprocess.run(
        ["uv", "cache", "dir"],
        cwd=root,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )

    assert Path(result.stdout.strip()).resolve() == root / ".uv-cache"
    assert ".uv-cache/" in (root / ".gitignore").read_text(encoding="utf-8").splitlines()
    configuration = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    assert ".uv-cache" in configuration["tool"]["ruff"]["extend-exclude"]
