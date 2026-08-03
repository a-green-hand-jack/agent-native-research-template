from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from test_research import build_repository

import evidence


def python_command(source: str) -> list[str]:
    return [sys.executable, "-c", source]


def configure_phase_spec(root: Path) -> Path:
    spec_path = build_repository(root)
    generation = (
        "from pathlib import Path; "
        "count=Path('generation-count.txt'); "
        "count.write_text(str(int(count.read_text()) + 1) if count.exists() else '1'); "
        "Path('outputs').mkdir(exist_ok=True); "
        "Path('outputs/generated.txt').write_text('generated\\n')"
    )
    evaluation = (
        "import os; from pathlib import Path; "
        "source=Path(os.environ['RESEARCH_PHASE_GENERATION_ARTIFACT_DIR']); "
        "assert next(source.rglob('generated.txt')).read_text() == 'generated\\n'; "
        "Path('outputs/score.txt').write_text('1\\n')"
    )
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    spec.pop("command", None)
    spec["phases"] = [
        {
            "id": "generation",
            "command": python_command(generation),
            "asset_phase": "generation",
            "outputs": [{"path": "outputs/generated.txt", "required": True}],
        },
        {
            "id": "evaluation",
            "command": python_command(evaluation),
            "depends_on": ["generation"],
            "asset_phase": "evaluation",
            "outputs": [{"path": "outputs/score.txt", "required": True}],
        },
    ]
    spec_path.write_text(yaml.safe_dump(spec, sort_keys=False), encoding="utf-8")
    return spec_path


def test_retry_phase_skips_generation_and_records_reuse(tmp_path: Path) -> None:
    spec_path = configure_phase_spec(tmp_path)
    parent_path, parent_code = evidence.run_spec(spec_path, tmp_path)
    assert parent_code == 0
    parent = json.loads(parent_path.read_text(encoding="utf-8"))
    assert (tmp_path / "generation-count.txt").read_text(encoding="utf-8") == "1"

    retry_path, retry_code = evidence.retry_phase_run(parent["run_id"], "evaluation", tmp_path)
    assert retry_code == 0
    retry = json.loads(retry_path.read_text(encoding="utf-8"))
    assert retry["parent_run_id"] == parent["run_id"]
    assert retry["recovery"]["retry_phase"] == "evaluation"
    assert retry["recovery"]["generation_skipped"] is True
    assert retry["phases"][0]["status"] == "reused"
    assert retry["phases"][1]["status"] == "succeeded"
    assert (tmp_path / "generation-count.txt").read_text(encoding="utf-8") == "1"
    assert evidence.verify_run(retry["run_id"], tmp_path)["run_id"] == retry["run_id"]
