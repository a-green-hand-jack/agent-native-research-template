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


def patch_asset_helper() -> None:
    replace_once(
        "tools/asset_binding.py",
        "    registry = load_registry(root)\n"
        "    requirements = requirement_records(spec)\n"
        "    bindings = executor.get(\"asset_bindings\", {})\n",
        "    requirements = requirement_records(spec)\n"
        "    if not requirements:\n"
        "        empty = {\"phase\": phase, \"assets\": []}\n"
        "        return {**empty, \"sha256\": canonical_hash(empty)}\n"
        "    registry = load_registry(root)\n"
        "    bindings = executor.get(\"asset_bindings\", {})\n",
    )


def patch_evidence() -> None:
    replace_once(
        "tools/evidence.py",
        "import experiment_plan\nimport input_identity\nimport research\n",
        "import asset_binding\nimport experiment_plan\nimport input_identity\nimport research\n",
    )
    replace_once(
        "tools/evidence.py",
        "    seed, timeout = supported_execution_controls(resolved[\"spec\"])\n"
        "    return {\n"
        "        **resolved,\n"
        "        \"seed\": seed,\n"
        "        \"timeout\": timeout,\n"
        "        \"plan\": plan[\"resolved\"],\n"
        "        \"plan_sha256\": plan[\"sha256\"],\n"
        "    }\n",
        "    preflight = asset_binding.resolve_assets(\n"
        "        resolved[\"spec\"], resolved[\"executor\"], root, phase=\"all\"\n"
        "    )\n"
        "    seed, timeout = supported_execution_controls(resolved[\"spec\"])\n"
        "    return {\n"
        "        **resolved,\n"
        "        \"seed\": seed,\n"
        "        \"timeout\": timeout,\n"
        "        \"plan\": plan[\"resolved\"],\n"
        "        \"plan_sha256\": plan[\"sha256\"],\n"
        "        \"asset_preflight\": preflight,\n"
        "    }\n",
    )
    replace_once(
        "tools/evidence.py",
        "    environment = os.environ.copy()\n"
        "    environment[SEED_ENVIRONMENT_VARIABLE] = str(seed)\n",
        "    environment = os.environ.copy()\n"
        "    environment[SEED_ENVIRONMENT_VARIABLE] = str(seed)\n"
        "    environment.update(asset_binding.environment_for_assets(resolved[\"asset_preflight\"]))\n",
    )
    replace_once(
        "tools/evidence.py",
        "        \"data\": spec.get(\"data\"),\n"
        "        \"inputs\": resolved[\"inputs\"],\n"
        "        \"spec\": {\n",
        "        \"data\": spec.get(\"data\"),\n"
        "        \"inputs\": resolved[\"inputs\"],\n"
        "        \"asset_bindings\": resolved[\"asset_preflight\"],\n"
        "        \"spec\": {\n",
    )
    replace_once(
        "tools/evidence.py",
        "    drift.extend(input_identity.recorded_input_drift(manifest.get(\"inputs\", []), root))\n"
        "    return drift\n",
        "    drift.extend(input_identity.recorded_input_drift(manifest.get(\"inputs\", []), root))\n"
        "    asset_records = manifest.get(\"asset_bindings\", {}).get(\"assets\", [])\n"
        "    drift.extend(asset_binding.recorded_asset_drift(asset_records, root))\n"
        "    return drift\n",
    )
    replace_once(
        "tools/evidence.py",
        "    plan = subparsers.add_parser(\"plan\", help=\"emit a deterministic side-effect-free plan\")\n"
        "    plan.add_argument(\"spec\")\n\n"
        "    run = subparsers.add_parser(\"run\", help=\"run one supported spec with full evidence extraction\")\n",
        "    plan = subparsers.add_parser(\"plan\", help=\"emit a deterministic side-effect-free plan\")\n"
        "    plan.add_argument(\"spec\")\n\n"
        "    preflight = subparsers.add_parser(\n"
        "        \"preflight\", help=\"resolve and validate logical asset bindings\"\n"
        "    )\n"
        "    preflight.add_argument(\"spec\")\n"
        "    preflight.add_argument(\"--phase\", choices=sorted(asset_binding.PHASES), default=\"all\")\n\n"
        "    run = subparsers.add_parser(\"run\", help=\"run one supported spec with full evidence extraction\")\n",
    )
    replace_once(
        "tools/evidence.py",
        "        if args.command == \"run\":\n"
        "            path, code = run_spec(root / args.spec, root, parent_run_id=args.parent)\n",
        "        if args.command == \"preflight\":\n"
        "            resolved = research.validate_spec(root / args.spec, root)\n"
        "            preflight = asset_binding.resolve_assets(\n"
        "                resolved[\"spec\"], resolved[\"executor\"], root, phase=args.phase\n"
        "            )\n"
        "            print(json.dumps(preflight, indent=2, sort_keys=True))\n"
        "            return 0\n"
        "        if args.command == \"run\":\n"
        "            path, code = run_spec(root / args.spec, root, parent_run_id=args.parent)\n",
    )
    replace_once(
        "tools/evidence.py",
        "        EvidenceError,\n"
        "        experiment_plan.PlanError,\n",
        "        AssetBindingError if False else EvidenceError,\n"
        "        asset_binding.AssetBindingError,\n"
        "        experiment_plan.PlanError,\n",
    )
    replace_once(
        "tools/evidence.py",
        "        AssetBindingError if False else EvidenceError,\n",
        "        EvidenceError,\n",
    )


def patch_plan() -> None:
    replace_once(
        "tools/experiment_plan.py",
        "        \"inputs\": deepcopy(spec.get(\"inputs\", [])),\n"
        "        \"artifacts\": deepcopy(spec.get(\"artifacts\", [])),\n",
        "        \"inputs\": deepcopy(spec.get(\"inputs\", [])),\n"
        "        \"assets\": deepcopy(spec.get(\"assets\", [])),\n"
        "        \"artifacts\": deepcopy(spec.get(\"artifacts\", [])),\n",
    )


def patch_research() -> None:
    replace_once(
        "tools/research.py",
        "    \"executor\": \"schemas/executor.schema.json\",\n"
        "    \"run manifest\": \"schemas/run-manifest.schema.json\",\n",
        "    \"executor\": \"schemas/executor.schema.json\",\n"
        "    \"asset registry\": \"schemas/asset-registry.schema.json\",\n"
        "    \"run manifest\": \"schemas/run-manifest.schema.json\",\n",
    )


def patch_schemas() -> None:
    experiment_path = ROOT / "schemas/experiment.schema.json"
    experiment = json.loads(experiment_path.read_text(encoding="utf-8"))
    experiment["$defs"]["asset_requirement"] = {
        "type": "object",
        "required": ["id"],
        "properties": {
            "id": {"$ref": "#/$defs/identifier"},
            "phase": {"enum": ["all", "generation", "evaluation"]},
            "access": {"enum": ["read", "write"]},
        },
        "additionalProperties": False,
    }
    experiment["properties"]["assets"] = {
        "type": "array",
        "items": {"$ref": "#/$defs/asset_requirement"},
    }
    experiment_path.write_text(json.dumps(experiment, indent=2) + "\n", encoding="utf-8")

    executor_path = ROOT / "schemas/executor.schema.json"
    executor = json.loads(executor_path.read_text(encoding="utf-8"))
    executor["$defs"] = {
        "binding": {
            "oneOf": [
                {
                    "type": "object",
                    "required": ["kind", "path"],
                    "properties": {
                        "kind": {"const": "path"},
                        "scope": {"enum": ["repository", "external"]},
                        "path": {"type": "string", "minLength": 1},
                        "sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
                    },
                    "additionalProperties": False,
                },
                {
                    "type": "object",
                    "required": ["kind", "uri"],
                    "properties": {
                        "kind": {"const": "uri"},
                        "uri": {"type": "string", "minLength": 1},
                        "version": {"type": "string", "minLength": 1},
                        "sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
                    },
                    "additionalProperties": False,
                },
                {
                    "type": "object",
                    "required": ["kind", "value"],
                    "properties": {
                        "kind": {"const": "opaque"},
                        "value": {"type": "string", "minLength": 1},
                        "version": {"type": "string", "minLength": 1},
                    },
                    "additionalProperties": False,
                },
            ]
        }
    }
    executor["properties"]["asset_bindings"] = {
        "type": "object",
        "additionalProperties": {"$ref": "#/$defs/binding"},
    }
    executor_path.write_text(json.dumps(executor, indent=2) + "\n", encoding="utf-8")

    run_path = ROOT / "schemas/run-manifest.schema.json"
    run = json.loads(run_path.read_text(encoding="utf-8"))
    run["required"].insert(run["required"].index("spec"), "asset_bindings")
    run["properties"]["asset_bindings"] = {
        "type": "object",
        "required": ["phase", "assets", "sha256"],
        "properties": {
            "phase": {"enum": ["all", "generation", "evaluation"]},
            "assets": {"type": "array", "items": {"type": "object"}},
            "sha256": {"$ref": "#/$defs/sha256"},
        },
        "additionalProperties": False,
    }
    run_path.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")


def patch_examples() -> None:
    profile_path = ROOT / "infra/profiles/local.yaml"
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    profile["asset_bindings"] = {
        "source-tree": {"kind": "path", "scope": "repository", "path": "src"}
    }
    profile_path.write_text(yaml.safe_dump(profile, sort_keys=False), encoding="utf-8")

    spec_path = ROOT / "experiments/specs/smoke.yaml"
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    spec["assets"] = [{"id": "source-tree", "phase": "generation", "access": "read"}]
    spec_path.write_text(yaml.safe_dump(spec, sort_keys=False), encoding="utf-8")


def patch_docs() -> None:
    replace_once(
        ".agents/governance/CONTRACT.md",
        "- New runs resolve generic `path`, `uri`, and `opaque` input declarations before execution.\n",
        "- Logical assets have stable registry IDs and roles. Experiments name logical requirements,\n"
        "  executor profiles bind physical `path`, `uri`, or `opaque` records, and side-effect-free\n"
        "  preflight validates role, phase, access, type, size, checksum, path, and overwrite rules.\n"
        "  Scientific plan identity excludes physical bindings; run evidence records their resolved hash.\n"
        "- Generation preflight never exposes evaluation-only assets. Reading assets requires verified\n"
        "  presence and content identity; write targets may be planned but immutable outputs cannot be\n"
        "  overwritten.\n"
        "- New runs resolve generic `path`, `uri`, and `opaque` input declarations before execution.\n",
    )
    replace_once(
        ".agents/skills/run-experiment/SKILL.md",
        "uv run python tools/evidence.py plan experiments/specs/<name>.yaml\n",
        "uv run python tools/evidence.py plan experiments/specs/<name>.yaml\n"
        "uv run python tools/evidence.py preflight experiments/specs/<name>.yaml\n",
    )
    replace_once(
        ".agents/skills/run-experiment/SKILL.md",
        "Review the deterministic plan and its SHA-256 before execution. A multi-cell plan requires an\n",
        "Review the deterministic plan and its SHA-256, then review preflight's resolved logical asset\n"
        "bindings. Use `--phase generation` or `--phase evaluation` to prove oracle isolation.\n\n"
        "A multi-cell plan requires an\n",
    )
    units_path = ROOT / ".agents/governance/REPO_UNITS.yaml"
    units = yaml.safe_load(units_path.read_text(encoding="utf-8"))
    required = units["required_paths"]["functional"]
    for path in (
        "assets/registry.yaml",
        "docs/ASSET_BINDINGS.md",
        "schemas/asset-registry.schema.json",
        "tools/asset_binding.py",
    ):
        if path not in required:
            required.append(path)
    required.sort()
    units_path.write_text(yaml.safe_dump(units, sort_keys=False), encoding="utf-8")


def main() -> None:
    patch_asset_helper()
    patch_evidence()
    patch_plan()
    patch_research()
    patch_schemas()
    patch_examples()
    patch_docs()


if __name__ == "__main__":
    main()
