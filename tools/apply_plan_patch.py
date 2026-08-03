from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    content = target.read_text(encoding="utf-8")
    count = content.count(old)
    if count != 1:
        raise RuntimeError(f"expected one match in {path}, found {count}: {old!r}")
    target.write_text(content.replace(old, new), encoding="utf-8")


def patch_evidence() -> None:
    replace_once(
        "tools/evidence.py",
        "import input_identity\nimport research\n",
        "import experiment_plan\nimport input_identity\nimport research\n",
    )
    replace_once(
        "tools/evidence.py",
        "def validate_supported_spec(spec_path: Path, root: Path = ROOT) -> dict[str, Any]:\n"
        "    resolved = research.validate_spec(spec_path, root)\n"
        "    seed, timeout = supported_execution_controls(resolved[\"spec\"])\n"
        "    return {**resolved, \"seed\": seed, \"timeout\": timeout}\n",
        "def validate_supported_spec(spec_path: Path, root: Path = ROOT) -> dict[str, Any]:\n"
        "    resolved = research.validate_spec(spec_path, root)\n"
        "    plan = experiment_plan.build_plan(resolved)\n"
        "    if len(plan[\"resolved\"][\"cells\"]) != 1:\n"
        "        raise EvidenceError(\n"
        "            \"the local runner executes exactly one plan cell; use an external scheduler \"\n"
        "            \"for matrix plans\"\n"
        "        )\n"
        "    seed, timeout = supported_execution_controls(resolved[\"spec\"])\n"
        "    return {\n"
        "        **resolved,\n"
        "        \"seed\": seed,\n"
        "        \"timeout\": timeout,\n"
        "        \"plan\": plan[\"resolved\"],\n"
        "        \"plan_sha256\": plan[\"sha256\"],\n"
        "    }\n",
    )
    replace_once(
        "tools/evidence.py",
        "        \"question\": spec[\"question\"],\n"
        "        \"contribution\": spec[\"contribution\"],\n"
        "        \"config\": {\n",
        "        \"question\": spec[\"question\"],\n"
        "        \"contribution\": spec[\"contribution\"],\n"
        "        \"plan\": {\n"
        "            \"sha256\": resolved[\"plan_sha256\"],\n"
        "            \"resolved\": resolved[\"plan\"],\n"
        "        },\n"
        "        \"config\": {\n",
    )
    replace_once(
        "tools/evidence.py",
        "    run = subparsers.add_parser(\"run\", help=\"run one supported spec with full evidence extraction\")\n",
        "    plan = subparsers.add_parser(\"plan\", help=\"emit a deterministic side-effect-free plan\")\n"
        "    plan.add_argument(\"spec\")\n\n"
        "    run = subparsers.add_parser(\"run\", help=\"run one supported spec with full evidence extraction\")\n",
    )
    replace_once(
        "tools/evidence.py",
        "        if args.command == \"run\":\n"
        "            path, code = run_spec(root / args.spec, root, parent_run_id=args.parent)\n",
        "        if args.command == \"plan\":\n"
        "            print(experiment_plan.render_plan(root / args.spec, root), end=\"\")\n"
        "            return 0\n"
        "        if args.command == \"run\":\n"
        "            path, code = run_spec(root / args.spec, root, parent_run_id=args.parent)\n",
    )
    replace_once(
        "tools/evidence.py",
        "    except (EvidenceError, research.SpecError, OSError, ValueError) as exc:\n",
        "    except (\n"
        "        EvidenceError,\n"
        "        experiment_plan.PlanError,\n"
        "        research.SpecError,\n"
        "        OSError,\n"
        "        ValueError,\n"
        "    ) as exc:\n",
    )


def patch_schemas() -> None:
    experiment_path = ROOT / "schemas/experiment.schema.json"
    experiment = json.loads(experiment_path.read_text(encoding="utf-8"))
    experiment["$defs"]["json_scalar"] = {
        "type": ["string", "integer", "number", "boolean", "null"]
    }
    experiment["properties"].update(
        {
            "protocol_id": {"$ref": "#/$defs/identifier"},
            "run_class": {
                "enum": [
                    "smoke",
                    "pilot",
                    "partial",
                    "reference",
                    "formal",
                    "post_observation",
                ]
            },
            "observation_status": {"enum": ["pre_observation", "post_observation"]},
            "scientific_parameters": {
                "type": "object",
                "additionalProperties": {"$ref": "#/$defs/json_scalar"},
            },
            "matrix": {
                "type": "object",
                "additionalProperties": {
                    "type": "array",
                    "minItems": 1,
                    "items": {"$ref": "#/$defs/json_scalar"},
                },
            },
            "recovery_policy": {
                "type": "object",
                "properties": {
                    "mode": {"enum": ["new_run", "phase_retry"]},
                    "reuse_verified_artifacts": {"type": "boolean"},
                },
                "additionalProperties": false,
            },
            "completion_criteria": {
                "type": "object",
                "properties": {
                    "required_artifacts": {
                        "type": "array",
                        "items": {"type": "string", "minLength": 1},
                    },
                    "required_metrics": {
                        "type": "array",
                        "items": {"$ref": "#/$defs/identifier"},
                    },
                },
                "additionalProperties": false,
            },
        }
    )
    experiment_path.write_text(json.dumps(experiment, indent=2) + "\n", encoding="utf-8")

    run_path = ROOT / "schemas/run-manifest.schema.json"
    run = json.loads(run_path.read_text(encoding="utf-8"))
    run["required"].insert(run["required"].index("config"), "plan")
    run["properties"]["plan"] = {
        "type": "object",
        "required": ["sha256", "resolved"],
        "properties": {
            "sha256": {"$ref": "#/$defs/sha256"},
            "resolved": {"type": "object"},
        },
        "additionalProperties": false,
    }
    run_path.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")


def patch_documents() -> None:
    spec_path = ROOT / "experiments/specs/smoke.yaml"
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    spec["protocol_id"] = "smoke-v1"
    spec["run_class"] = "smoke"
    spec["observation_status"] = "pre_observation"
    spec["scientific_parameters"] = {}
    spec["recovery_policy"] = {"mode": "new_run", "reuse_verified_artifacts": False}
    spec["completion_criteria"] = {"required_artifacts": [], "required_metrics": ["success"]}
    spec_path.write_text(yaml.safe_dump(spec, sort_keys=False), encoding="utf-8")

    replace_once(
        ".agents/governance/CONTRACT.md",
        "- A runnable experiment resolves its code revision, config, environment, structured inputs,\n"
        "  executor, and evaluation protocol.\n",
        "- A runnable experiment resolves its code revision, config, environment, structured inputs,\n"
        "  executor, and evaluation protocol.\n"
        "- Every execution is preceded by a deterministic, side-effect-free plan. The plan records a\n"
        "  protocol ID, run class, observation status, scientific parameters, stable matrix cells,\n"
        "  resource controls, commands, declared inputs and artifacts, recovery policy, and completion\n"
        "  criteria. Canonical JSON supplies the plan SHA-256 recorded in run evidence.\n"
        "- Formal runs require an explicit pre-observation protocol. Post-observation analyses remain\n"
        "  traceable but cannot be relabeled as formal pre-observation evidence.\n",
    )
    replace_once(
        ".agents/skills/run-experiment/SKILL.md",
        "uv run python tools/research.py validate experiments/specs/<name>.yaml\n"
        "uv run python tools/evidence.py validate experiments/specs/<name>.yaml\n",
        "uv run python tools/research.py validate experiments/specs/<name>.yaml\n"
        "uv run python tools/evidence.py validate experiments/specs/<name>.yaml\n"
        "uv run python tools/evidence.py plan experiments/specs/<name>.yaml\n",
    )
    replace_once(
        ".agents/skills/run-experiment/SKILL.md",
        "Each execution receives a unique run ID and writes an ignored local manifest under\n",
        "Review the deterministic plan and its SHA-256 before execution. A multi-cell plan requires an\n"
        "external scheduler; the built-in runner executes exactly one cell.\n\n"
        "Each execution receives a unique run ID and writes an ignored local manifest under\n",
    )

    units_path = ROOT / ".agents/governance/REPO_UNITS.yaml"
    units = yaml.safe_load(units_path.read_text(encoding="utf-8"))
    required = units["required_paths"]["functional"]
    for path in ("docs/EXPERIMENT_PLANS.md", "tools/experiment_plan.py"):
        if path not in required:
            required.append(path)
    required.sort()
    units_path.write_text(yaml.safe_dump(units, sort_keys=False), encoding="utf-8")


def main() -> None:
    patch_evidence()
    patch_schemas()
    patch_documents()


if __name__ == "__main__":
    main()
