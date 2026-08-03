from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

ASSET_SPEC = importlib.util.spec_from_file_location("asset_binding_tool", TOOLS / "asset_binding.py")
assert ASSET_SPEC and ASSET_SPEC.loader
asset_binding = importlib.util.module_from_spec(ASSET_SPEC)
ASSET_SPEC.loader.exec_module(asset_binding)

PLAN_SPEC = importlib.util.spec_from_file_location("experiment_plan_tool", TOOLS / "experiment_plan.py")
assert PLAN_SPEC and PLAN_SPEC.loader
experiment_plan = importlib.util.module_from_spec(PLAN_SPEC)
PLAN_SPEC.loader.exec_module(experiment_plan)

import research
from test_research import build_repository


def configure_assets(root: Path) -> Path:
    spec_path = build_repository(root)
    registry = {
        "schema_version": 1,
        "assets": [
            {
                "id": "source-tree",
                "role": "source",
                "expected_type": "directory",
                "reconstructable": True,
                "min_bytes": 1,
            },
            {
                "id": "eval-oracle",
                "role": "evaluation_oracle",
                "expected_type": "file",
                "reconstructable": False,
            },
            {
                "id": "final-output",
                "role": "output",
                "expected_type": "file",
                "reconstructable": False,
                "immutable_output": True,
            },
        ],
    }
    registry_path = root / asset_binding.REGISTRY_PATH
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(yaml.safe_dump(registry, sort_keys=False), encoding="utf-8")
    (root / "src/model.py").parent.mkdir(parents=True, exist_ok=True)
    (root / "src/model.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "eval-oracle.json").write_text("{}\n", encoding="utf-8")
    executor_path = root / "infra/profiles/local.yaml"
    executor = yaml.safe_load(executor_path.read_text(encoding="utf-8"))
    executor["asset_bindings"] = {
        "source-tree": {"kind": "path", "scope": "repository", "path": "src"},
        "eval-oracle": {
            "kind": "path",
            "scope": "repository",
            "path": "eval-oracle.json",
        },
        "final-output": {
            "kind": "path",
            "scope": "repository",
            "path": "outputs/final.json",
        },
    }
    executor_path.write_text(yaml.safe_dump(executor, sort_keys=False), encoding="utf-8")
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    spec["assets"] = [
        {"id": "source-tree", "phase": "generation", "access": "read"},
        {"id": "eval-oracle", "phase": "evaluation", "access": "read"},
    ]
    spec_path.write_text(yaml.safe_dump(spec, sort_keys=False), encoding="utf-8")
    return spec_path


def resolved_spec(spec_path: Path, root: Path) -> dict[str, object]:
    return research.validate_spec(spec_path, root)


def test_preflight_resolves_content_identity(tmp_path: Path) -> None:
    spec_path = configure_assets(tmp_path)
    resolved = resolved_spec(spec_path, tmp_path)
    preflight = asset_binding.resolve_assets(
        resolved["spec"], resolved["executor"], tmp_path, phase="all"
    )
    assert [record["id"] for record in preflight["assets"]] == [
        "source-tree",
        "eval-oracle",
    ]
    source = preflight["assets"][0]
    assert source["path_type"] == "directory"
    assert source["file_count"] == 1
    assert len(source["sha256"]) == 64
    assert len(preflight["sha256"]) == 64


def test_generation_phase_excludes_evaluation_only_asset(tmp_path: Path) -> None:
    spec_path = configure_assets(tmp_path)
    resolved = resolved_spec(spec_path, tmp_path)
    preflight = asset_binding.resolve_assets(
        resolved["spec"], resolved["executor"], tmp_path, phase="generation"
    )
    assert [record["id"] for record in preflight["assets"]] == ["source-tree"]
    environment = asset_binding.environment_for_assets(preflight)
    assert "RESEARCH_ASSET_SOURCE_TREE" in environment
    assert "RESEARCH_ASSET_EVAL_ORACLE" not in environment


def test_profile_binding_change_does_not_change_scientific_plan(tmp_path: Path) -> None:
    spec_path = configure_assets(tmp_path)
    first = experiment_plan.plan_spec(spec_path, tmp_path)
    (tmp_path / "src-copy").mkdir()
    (tmp_path / "src-copy/model.py").write_text("VALUE = 1\n", encoding="utf-8")
    executor_path = tmp_path / "infra/profiles/local.yaml"
    executor = yaml.safe_load(executor_path.read_text(encoding="utf-8"))
    executor["asset_bindings"]["source-tree"]["path"] = "src-copy"
    executor_path.write_text(yaml.safe_dump(executor, sort_keys=False), encoding="utf-8")
    second = experiment_plan.plan_spec(spec_path, tmp_path)
    assert first == second
    resolved = resolved_spec(spec_path, tmp_path)
    preflight = asset_binding.resolve_assets(
        resolved["spec"], resolved["executor"], tmp_path, phase="generation"
    )
    assert preflight["assets"][0]["path"] == "src-copy"


def test_missing_binding_is_rejected(tmp_path: Path) -> None:
    spec_path = configure_assets(tmp_path)
    executor_path = tmp_path / "infra/profiles/local.yaml"
    executor = yaml.safe_load(executor_path.read_text(encoding="utf-8"))
    del executor["asset_bindings"]["eval-oracle"]
    executor_path.write_text(yaml.safe_dump(executor, sort_keys=False), encoding="utf-8")
    resolved = resolved_spec(spec_path, tmp_path)
    with pytest.raises(asset_binding.AssetBindingError, match="no binding"):
        asset_binding.resolve_assets(resolved["spec"], resolved["executor"], tmp_path)


def test_type_mismatch_is_rejected(tmp_path: Path) -> None:
    spec_path = configure_assets(tmp_path)
    executor_path = tmp_path / "infra/profiles/local.yaml"
    executor = yaml.safe_load(executor_path.read_text(encoding="utf-8"))
    executor["asset_bindings"]["eval-oracle"]["path"] = "src"
    executor_path.write_text(yaml.safe_dump(executor, sort_keys=False), encoding="utf-8")
    resolved = resolved_spec(spec_path, tmp_path)
    with pytest.raises(asset_binding.AssetBindingError, match="expected file"):
        asset_binding.resolve_assets(resolved["spec"], resolved["executor"], tmp_path)


def test_symlink_binding_is_rejected(tmp_path: Path) -> None:
    spec_path = configure_assets(tmp_path)
    (tmp_path / "linked-src").symlink_to(tmp_path / "src", target_is_directory=True)
    executor_path = tmp_path / "infra/profiles/local.yaml"
    executor = yaml.safe_load(executor_path.read_text(encoding="utf-8"))
    executor["asset_bindings"]["source-tree"]["path"] = "linked-src"
    executor_path.write_text(yaml.safe_dump(executor, sort_keys=False), encoding="utf-8")
    resolved = resolved_spec(spec_path, tmp_path)
    with pytest.raises(asset_binding.AssetBindingError, match="symbolic link"):
        asset_binding.resolve_assets(resolved["spec"], resolved["executor"], tmp_path)


def test_existing_immutable_output_is_rejected(tmp_path: Path) -> None:
    spec_path = configure_assets(tmp_path)
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    spec["assets"].append({"id": "final-output", "phase": "evaluation", "access": "write"})
    spec_path.write_text(yaml.safe_dump(spec, sort_keys=False), encoding="utf-8")
    output = tmp_path / "outputs/final.json"
    output.parent.mkdir(parents=True)
    output.write_text("{}\n", encoding="utf-8")
    resolved = resolved_spec(spec_path, tmp_path)
    with pytest.raises(asset_binding.AssetBindingError, match="already exists"):
        asset_binding.resolve_assets(resolved["spec"], resolved["executor"], tmp_path)
