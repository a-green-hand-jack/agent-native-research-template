from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from tools import external_facts


def write_fact(root: Path, *, valid_until: str, status: str = "VERIFIED") -> Path:
    schema = root / external_facts.FACT_SCHEMA
    schema.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(external_facts.ROOT / external_facts.FACT_SCHEMA, schema)
    path = root / "external-facts/platform.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    fact = {
        "schema_version": 1,
        "id": "platform-api",
        "statement": "The official API endpoint is available.",
        "source_url": "https://example.invalid/official",
        "checked_at": "2026-08-01T00:00:00Z",
        "valid_until": valid_until,
        "status": status,
        "scope": ["api", "platform"],
        "verification_method": "authenticated smoke request",
    }
    path.write_text(yaml.safe_dump(fact, sort_keys=False), encoding="utf-8")
    return path


def test_verified_fact_resolves_with_content_identity(tmp_path: Path) -> None:
    write_fact(tmp_path, valid_until="2026-09-01T00:00:00Z")
    resolved = external_facts.resolve_references(
        ["platform-api"], tmp_path, now=datetime(2026, 8, 5, tzinfo=UTC)
    )
    assert resolved[0]["effective_status"] == "VERIFIED"
    assert len(resolved[0]["sha256"]) == 64


def test_expired_verified_fact_becomes_stale_without_rewriting_source(tmp_path: Path) -> None:
    path = write_fact(tmp_path, valid_until="2026-08-02T00:00:00Z")
    before = path.read_text(encoding="utf-8")
    resolved = external_facts.resolve_references(
        ["platform-api"], tmp_path, now=datetime(2026, 8, 5, tzinfo=UTC)
    )
    assert resolved[0]["declared_status"] == "VERIFIED"
    assert resolved[0]["effective_status"] == "STALE"
    assert path.read_text(encoding="utf-8") == before


def test_unverified_fact_cannot_support_execution_or_release(tmp_path: Path) -> None:
    write_fact(tmp_path, valid_until="2026-09-01T00:00:00Z", status="UNVERIFIED")
    resolved = external_facts.resolve_references(
        ["platform-api"], tmp_path, now=datetime(2026, 8, 5, tzinfo=UTC)
    )
    with pytest.raises(external_facts.ExternalFactError, match="requires VERIFIED"):
        external_facts.require_verified(resolved, "experiment execution")


def test_refresh_rejects_fact_changed_after_plan_or_build(tmp_path: Path) -> None:
    path = write_fact(tmp_path, valid_until="2026-09-01T00:00:00Z")
    resolved = external_facts.resolve_references(
        ["platform-api"], tmp_path, now=datetime(2026, 8, 5, tzinfo=UTC)
    )
    path.write_text(path.read_text(encoding="utf-8") + "# changed\n", encoding="utf-8")
    with pytest.raises(external_facts.ExternalFactError, match="changed after"):
        external_facts.refresh_and_compare(resolved, tmp_path)


def test_unreferenced_malformed_fact_is_inert(tmp_path: Path) -> None:
    write_fact(tmp_path, valid_until="2026-09-01T00:00:00Z")
    (tmp_path / "external-facts/broken.yaml").write_text("[not: valid", encoding="utf-8")
    resolved = external_facts.resolve_references(
        ["platform-api"], tmp_path, now=datetime(2026, 8, 5, tzinfo=UTC)
    )
    assert [fact["id"] for fact in resolved] == ["platform-api"]
