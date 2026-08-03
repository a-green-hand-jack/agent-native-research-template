from __future__ import annotations

import json
from pathlib import Path

import yaml
from test_evidence import configure_outputs

from tools import evidence


def load(path: Path) -> dict[str, object]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def write(path: Path, value: dict[str, object]) -> None:
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def run(root: Path) -> tuple[Path, dict[str, object]]:
    spec = configure_outputs(root)
    manifest_path, code = evidence.run_spec(spec, root)
    assert code == 0
    return manifest_path, json.loads(manifest_path.read_text(encoding="utf-8"))


def test_run_and_terminal_result_record_all_identity_layers(tmp_path: Path) -> None:
    manifest_path, manifest = run(tmp_path)
    plan = manifest["plan"]
    assert plan["sha256"] == plan["execution"]["sha256"]
    assert plan["resolved"] == plan["execution"]["resolved"]
    result = json.loads((manifest_path.parent / "result.json").read_text(encoding="utf-8"))
    assert result["result_version"] == 2
    assert result["identities"] == {
        "protocol_sha256": plan["protocol"]["sha256"],
        "execution_plan_sha256": plan["execution"]["sha256"],
        "binding_sha256": plan["binding"]["sha256"],
    }


def test_protocol_drift_is_reported_separately(tmp_path: Path) -> None:
    _, manifest = run(tmp_path)
    spec_path = tmp_path / manifest["spec"]["path"]
    spec = load(spec_path)
    spec["scientific_parameters"] = {"temperature": 0.4}
    write(spec_path, spec)
    drift = evidence.recorded_plan_identity_drift(manifest, tmp_path)
    assert "protocol identity changed" in drift
    assert "execution plan identity changed" in drift
    assert "binding identity changed" not in drift


def test_config_drift_changes_execution_only(tmp_path: Path) -> None:
    _, manifest = run(tmp_path)
    (tmp_path / "configs/base.yaml").write_text("seed: 1\n", encoding="utf-8")
    drift = evidence.recorded_plan_identity_drift(manifest, tmp_path)
    assert drift == ["execution plan identity changed"]


def test_profile_drift_changes_binding_only(tmp_path: Path) -> None:
    _, manifest = run(tmp_path)
    profile_path = tmp_path / "infra/profiles/local.yaml"
    profile = load(profile_path)
    profile["environment"] = {"PYTHONUNBUFFERED": "1", "WORKERS": "2"}
    write(profile_path, profile)
    drift = evidence.recorded_plan_identity_drift(manifest, tmp_path)
    assert drift == ["binding identity changed"]
