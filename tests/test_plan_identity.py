from __future__ import annotations

from pathlib import Path

import yaml

from tools import asset_binding, experiment_plan, plan_identity, research

from test_research import build_repository


def load_yaml(path: Path) -> dict[str, object]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def write_yaml(path: Path, value: dict[str, object]) -> None:
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def plan(spec_path: Path, root: Path) -> dict[str, object]:
    return experiment_plan.plan_spec(spec_path, root)


def test_legacy_aliases_identify_the_execution_projection(tmp_path: Path) -> None:
    spec_path = build_repository(tmp_path)
    bundle = plan(spec_path, tmp_path)
    assert bundle["sha256"] == bundle["execution"]["sha256"]
    assert bundle["resolved"] == bundle["execution"]["resolved"]
    assert plan_identity.identity_summary(bundle) == {
        "protocol_sha256": bundle["protocol"]["sha256"],
        "execution_plan_sha256": bundle["execution"]["sha256"],
        "binding_sha256": bundle["binding"]["sha256"],
    }


def test_scientific_parameter_changes_protocol_and_execution_only(tmp_path: Path) -> None:
    spec_path = build_repository(tmp_path)
    first = plan(spec_path, tmp_path)
    spec = load_yaml(spec_path)
    spec["scientific_parameters"] = {"temperature": 0.2}
    write_yaml(spec_path, spec)
    second = plan(spec_path, tmp_path)
    assert first["protocol"]["sha256"] != second["protocol"]["sha256"]
    assert first["execution"]["sha256"] != second["execution"]["sha256"]
    assert first["binding"]["sha256"] == second["binding"]["sha256"]


def test_config_content_changes_execution_but_not_protocol_or_binding(tmp_path: Path) -> None:
    spec_path = build_repository(tmp_path)
    first = plan(spec_path, tmp_path)
    (tmp_path / "configs/base.yaml").write_text("seed: 1\n", encoding="utf-8")
    second = plan(spec_path, tmp_path)
    assert first["protocol"]["sha256"] == second["protocol"]["sha256"]
    assert first["execution"]["sha256"] != second["execution"]["sha256"]
    assert first["binding"]["sha256"] == second["binding"]["sha256"]


def test_phase_command_changes_execution_but_not_protocol_topology(tmp_path: Path) -> None:
    spec_path = build_repository(tmp_path)
    spec = load_yaml(spec_path)
    command = spec.pop("command")
    spec["phases"] = [{"id": "main", "command": command}]
    write_yaml(spec_path, spec)
    first = plan(spec_path, tmp_path)
    spec["phases"][0]["command"] = ["make", "smoke", "EXTRA=1"]
    write_yaml(spec_path, spec)
    second = plan(spec_path, tmp_path)
    assert first["protocol"]["sha256"] == second["protocol"]["sha256"]
    assert first["execution"]["sha256"] != second["execution"]["sha256"]
    assert first["binding"]["sha256"] == second["binding"]["sha256"]


def test_evaluation_protocol_changes_protocol_and_execution(tmp_path: Path) -> None:
    spec_path = build_repository(tmp_path)
    first = plan(spec_path, tmp_path)
    evaluation_path = tmp_path / "evals/smoke.yaml"
    evaluation = load_yaml(evaluation_path)
    evaluation["purpose"] = "a changed scientific interpretation"
    write_yaml(evaluation_path, evaluation)
    second = plan(spec_path, tmp_path)
    assert first["protocol"]["sha256"] != second["protocol"]["sha256"]
    assert first["execution"]["sha256"] != second["execution"]["sha256"]
    assert first["binding"]["sha256"] == second["binding"]["sha256"]


def test_profile_changes_binding_without_changing_protocol_or_execution(tmp_path: Path) -> None:
    spec_path = build_repository(tmp_path)
    first = plan(spec_path, tmp_path)
    profile_path = tmp_path / "infra/profiles/local.yaml"
    profile = load_yaml(profile_path)
    profile["environment"] = {"PYTHONUNBUFFERED": "1", "WORKERS": "2"}
    write_yaml(profile_path, profile)
    second = plan(spec_path, tmp_path)
    assert first["protocol"]["sha256"] == second["protocol"]["sha256"]
    assert first["execution"]["sha256"] == second["execution"]["sha256"]
    assert first["binding"]["sha256"] != second["binding"]["sha256"]


def test_resolved_assets_change_only_the_binding_identity(tmp_path: Path) -> None:
    spec_path = build_repository(tmp_path)
    resolved = research.validate_spec(spec_path, tmp_path)
    bundle = experiment_plan.build_plan(resolved)
    preflight = asset_binding.resolve_assets(
        resolved["spec"], resolved["executor"], tmp_path, phase="all"
    )
    bound = plan_identity.resolve_binding(bundle, preflight)
    assert bundle["protocol"] == bound["protocol"]
    assert bundle["execution"] == bound["execution"]
    assert bundle["binding"]["sha256"] != bound["binding"]["sha256"]
    assert bound["binding"]["resolved"]["binding_state"] == "resolved"
    assert bound["binding"]["resolved"]["asset_preflight_sha256"] == preflight["sha256"]
