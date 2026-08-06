from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / "initialize_project.py"
SPEC = importlib.util.spec_from_file_location("agent_home_initializer", MODULE)
assert SPEC and SPEC.loader
initializer = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = initializer
SPEC.loader.exec_module(initializer)


def test_downstream_agent_home_is_project_owned_and_minimal() -> None:
    targets = set(initializer.DOWNSTREAM_AGENT_FILES)
    assert targets == {
        "AGENTS.md",
        ".agents/system/manifest.yaml",
        ".agents/knowledge/README.md",
        ".agents/skills/README.md",
        ".agents/memory/README.md",
        ".agents/runtime/.gitignore",
    }
    assert not any("governance" in path for path in targets)


def test_agent_home_templates_route_through_project_cli() -> None:
    identity = initializer.ProjectIdentity(
        project_name="Example Project",
        distribution_name="example-project",
        package_name="example_project",
        cli_name="example",
        contribution_id="core",
    )
    rendered = initializer.render_downstream_agent_file(
        initializer.DOWNSTREAM_AGENT_DEFAULTS["AGENTS.md"], identity
    )
    assert "example project describe --json" in rendered
    assert "Do not implement project behavior under `.agents/`" in rendered
