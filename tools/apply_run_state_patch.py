from __future__ import annotations

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
        "import research\n",
        "import research\nimport run_state\n",
    )
    replace_once(
        "tools/evidence.py",
        "    run_dir = root / \"runs\" / run_id\n"
        "    run_dir.mkdir(parents=True, exist_ok=False)\n\n"
        "    environment = os.environ.copy()\n",
        "    run_dir = root / \"runs\" / run_id\n"
        "    run_dir.mkdir(parents=True, exist_ok=False)\n"
        "    run_state.write_progress(run_dir, \"planned\", plan_sha256=resolved[\"plan_sha256\"])\n"
        "    run_state.write_progress(run_dir, \"submitted\", executor=spec[\"executor\"])\n\n"
        "    environment = os.environ.copy()\n",
    )
    replace_once(
        "tools/evidence.py",
        "    started_at = utc_now()\n"
        "    execution = phase_graph.execute_phases(\n",
        "    started_at = utc_now()\n"
        "    run_state.write_progress(run_dir, \"running\", started_at=started_at)\n"
        "    execution = phase_graph.execute_phases(\n",
    )
    replace_once(
        "tools/evidence.py",
        "    research.validate_document(manifest, \"run manifest\", manifest_path, root)\n"
        "    research.write_json(manifest_path, manifest)\n"
        "    return manifest_path, manifest[\"return_code\"] or (3 if errors else 0)\n",
        "    research.validate_document(manifest, \"run manifest\", manifest_path, root)\n"
        "    research.write_json(manifest_path, manifest)\n"
        "    manifest_sha256 = research.sha256_file(manifest_path)\n"
        "    result_path = run_state.write_terminal_result(\n"
        "        manifest_path, manifest, manifest_sha256\n"
        "    )\n"
        "    result = research.load_json(result_path)\n"
        "    research.validate_document(result, \"run result\", result_path, root)\n"
        "    code = manifest[\"return_code\"] or (3 if result[\"state\"] != \"succeeded\" else 0)\n"
        "    return manifest_path, code\n",
    )
    replace_once(
        "tools/evidence.py",
        "    for artifact in manifest.get(\"artifacts\", []):\n",
        "    result_path = source.parent / \"result.json\"\n"
        "    if result_path.is_file():\n"
        "        result = research.load_json(result_path)\n"
        "        research.validate_document(result, \"run result\", result_path, root)\n"
        "        if result.get(\"manifest_sha256\") != research.sha256_file(source):\n"
        "            raise EvidenceError(\"terminal result manifest checksum mismatch\")\n"
        "    for artifact in manifest.get(\"artifacts\", []):\n",
    )
    helpers = '''def run_directory(value: str, root: Path = ROOT) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        run_dir = candidate
    elif candidate.parts and candidate.parts[0] == "runs":
        run_dir = root / candidate
    else:
        run_dir = root / "runs" / value
    return run_dir.resolve()


def run_status(value: str, root: Path = ROOT) -> dict[str, Any]:
    return run_state.status_projection(run_directory(value, root))


def run_results(value: str, root: Path = ROOT) -> dict[str, Any]:
    source = research.resolve_manifest(root, value)
    manifest = research.load_json(source)
    return run_state.results_projection(manifest, run_state.status_projection(source.parent))


def verified_status(value: str, root: Path = ROOT) -> dict[str, Any]:
    manifest = verify_run(value, root)
    source = research.resolve_manifest(root, value)
    status = run_state.status_projection(source.parent, verified=True)
    return {**status, "run_id": manifest["run_id"]}


'''
    replace_once(
        "tools/evidence.py",
        "def recorded_input_drift(",
        helpers + "def recorded_input_drift(",
    )
    replace_once(
        "tools/evidence.py",
        "    verify = subparsers.add_parser(\"verify-run\", help=\"verify every recorded artifact\")\n"
        "    verify.add_argument(\"run\")\n\n",
        "    status = subparsers.add_parser(\"status\", help=\"read evidence-first lifecycle status\")\n"
        "    status.add_argument(\"run\")\n\n"
        "    results = subparsers.add_parser(\"results\", help=\"read structured run results\")\n"
        "    results.add_argument(\"run\")\n\n"
        "    verify = subparsers.add_parser(\"verify-run\", help=\"verify every recorded artifact\")\n"
        "    verify.add_argument(\"run\")\n\n",
    )
    replace_once(
        "tools/evidence.py",
        "        if args.command == \"verify-run\":\n"
        "            manifest = verify_run(args.run, root)\n"
        "            print(f\"OK {manifest['run_id']}\")\n"
        "            return 0\n",
        "        if args.command == \"status\":\n"
        "            print(json.dumps(run_status(args.run, root), indent=2, sort_keys=True))\n"
        "            return 0\n"
        "        if args.command == \"results\":\n"
        "            print(json.dumps(run_results(args.run, root), indent=2, sort_keys=True))\n"
        "            return 0\n"
        "        if args.command == \"verify-run\":\n"
        "            print(json.dumps(verified_status(args.run, root), indent=2, sort_keys=True))\n"
        "            return 0\n",
    )
    replace_once(
        "tools/evidence.py",
        "        research.SpecError,\n",
        "        research.SpecError,\n        run_state.RunStateError,\n",
    )


def patch_research() -> None:
    replace_once(
        "tools/research.py",
        "    \"run manifest\": \"schemas/run-manifest.schema.json\",\n"
        "    \"evidence manifest\": \"schemas/evidence-manifest.schema.json\",\n",
        "    \"run manifest\": \"schemas/run-manifest.schema.json\",\n"
        "    \"run result\": \"schemas/run-result.schema.json\",\n"
        "    \"evidence manifest\": \"schemas/evidence-manifest.schema.json\",\n",
    )


def patch_docs() -> None:
    replace_once(
        ".agents/governance/CONTRACT.md",
        "- Run facts are immutable. Retries create new runs linked to their parent.\n",
        "- Run lifecycle is evidence-first. Atomic progress records may be planned, submitted, or\n"
        "  running. Only a validated terminal result may be failed, incomplete, or succeeded; verified\n"
        "  is a read-only projection after manifest and artifact verification. Missing or corrupt\n"
        "  terminal evidence never implies success.\n"
        "- Completion criteria require declared artifacts, metrics, and terminal phase results in\n"
        "  addition to process return codes. Status and results commands read recorded evidence only;\n"
        "  they never infer completion from process disappearance or hardware idleness.\n"
        "- Run facts are immutable. Retries create new runs linked to their parent.\n",
    )
    replace_once(
        ".agents/skills/run-experiment/SKILL.md",
        "uv run python tools/evidence.py verify-run <run-id>\n",
        "uv run python tools/evidence.py status <run-id>\n"
        "uv run python tools/evidence.py results <run-id>\n"
        "uv run python tools/evidence.py verify-run <run-id>\n",
    )
    replace_once(
        "evidence/manifests/README.md",
        "Promote a run only after its artifact checksums and interpretation have been reviewed. Evidence\n",
        "A run's `state.json` is non-terminal progress; `result.json` is the atomic terminal completion\n"
        "record. Status is never inferred from process or accelerator idleness. Missing terminal evidence\n"
        "is incomplete, and verification is a read-only projection rather than a mutation.\n\n"
        "Promote a run only after its artifact checksums and interpretation have been reviewed. Evidence\n",
    )
    units_path = ROOT / ".agents/governance/REPO_UNITS.yaml"
    units = yaml.safe_load(units_path.read_text(encoding="utf-8"))
    required = units["required_paths"]["functional"]
    for path in ("docs/RUN_STATUS.md", "schemas/run-result.schema.json", "tools/run_state.py"):
        if path not in required:
            required.append(path)
    required.sort()
    units_path.write_text(yaml.safe_dump(units, sort_keys=False), encoding="utf-8")


def main() -> None:
    patch_evidence()
    patch_research()
    patch_docs()


if __name__ == "__main__":
    main()
