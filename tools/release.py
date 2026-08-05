from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from . import archive, external_facts

ROOT = Path(__file__).resolve().parents[1]
RELEASE_VERSION = 1
PROFILE_SCHEMA = Path("schemas/release.schema.json")
MANIFEST_SCHEMA = Path("schemas/release-manifest.schema.json")
DEFAULT_PROFILE = Path("RELEASE.yaml")
FORBIDDEN_RELEASE_ROOTS = {".agents", ".git", ".omx", ".venv", "dist", "runs"}
RELEASE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
CLEAN_STATE_SHA256 = hashlib.sha256(b"\0").hexdigest()


class ReleaseError(ValueError):
    """Raised when a release profile, artifact, or approval is invalid."""


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ReleaseError(f"cannot read release profile {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ReleaseError(f"release profile must be a mapping: {path}")
    return value


def validate(value: dict[str, Any], schema_path: Path, source: Path, root: Path) -> None:
    schema = json.loads((root / schema_path).read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(value),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.absolute_path) or "$"
        raise ReleaseError(f"{source} does not match release schema at {location}: {error.message}")


def repository_path(root: Path, value: str) -> Path:
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ReleaseError(f"release path must be repository-relative: {value}")
    if relative.parts and relative.parts[0] in FORBIDDEN_RELEASE_ROOTS:
        raise ReleaseError(f"release profile cannot include managed or governance path: {value}")
    path = root / relative
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ReleaseError(f"release path escapes repository: {value}") from exc
    if not path.exists() or path.is_symlink():
        raise ReleaseError(f"release path is missing or symbolic: {value}")
    return path


def managed_path(root: Path, relative: Path) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise ReleaseError(f"managed release path must be repository-relative: {relative}")
    root_path = Path(os.path.abspath(root))
    path = root_path
    for part in relative.parts:
        path /= part
        if path.is_symlink():
            raise ReleaseError(f"managed release path contains a symbolic link: {relative}")
    try:
        path.resolve(strict=False).relative_to(root_path.resolve())
    except ValueError as exc:
        raise ReleaseError(f"managed release path escapes repository: {relative}") from exc
    return path


def included_files(root: Path, profile: dict[str, Any]) -> list[Path]:
    files: set[Path] = set()
    for relative in profile["include"]:
        path = repository_path(root, relative)
        if path.is_file():
            files.add(path)
        else:
            for candidate in path.rglob("*"):
                if candidate.is_symlink():
                    raise ReleaseError(f"release tree contains symbolic link: {candidate}")
                if candidate.is_file():
                    files.add(candidate)
    if not files:
        raise ReleaseError("release profile includes no files")
    return sorted(files)


def source_identity(root: Path) -> tuple[str, str]:
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=False, capture_output=True, text=True
    )
    if revision.returncode != 0:
        raise ReleaseError("release build requires a Git repository")
    diff = subprocess.run(
        ["git", "diff", "--binary", "HEAD"], cwd=root, check=False, capture_output=True
    )
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        cwd=root,
        check=False,
        capture_output=True,
    )
    if diff.returncode != 0 or untracked.returncode != 0:
        raise ReleaseError("cannot determine whether the release source checkout is clean")
    untracked_content = bytearray()
    for raw_path in sorted(path for path in untracked.stdout.split(b"\0") if path):
        path = root / os.fsdecode(raw_path)
        untracked_content.extend(raw_path)
        untracked_content.extend(b"\0")
        if path.is_file() and not path.is_symlink():
            untracked_content.extend(path.read_bytes())
        untracked_content.extend(b"\0")
    digest = hashlib.sha256(diff.stdout + b"\0" + untracked_content).hexdigest()
    return revision.stdout.strip(), digest


def release_layout(manifest_path: Path, manifest: dict[str, Any], root: Path) -> tuple[Path, Path]:
    identifier = manifest["release_id"]
    if not RELEASE_ID_PATTERN.fullmatch(identifier):
        raise ReleaseError("release manifest has an invalid release ID")
    expected_root = managed_path(root, Path("dist") / identifier)
    canonical_manifest = managed_path(root, Path("dist") / identifier / manifest_path.name)
    if Path(os.path.abspath(manifest_path)) != canonical_manifest or manifest_path.name not in {
        "manifest.json",
        "approved-manifest.json",
    }:
        raise ReleaseError("release manifest is outside its canonical dist directory")
    artifact_value = Path(manifest["artifact"]["path"])
    expected_artifact = managed_path(root, Path("dist") / identifier / "artifact.zip")
    if (
        artifact_value.is_absolute()
        or ".." in artifact_value.parts
        or Path(os.path.abspath(root / artifact_value)) != expected_artifact
    ):
        raise ReleaseError("release artifact path does not match the canonical release layout")
    return expected_root, expected_artifact


def authoritative_profile(
    manifest: dict[str, Any], root: Path
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    profile_path = repository_path(root, manifest["profile"]["path"])
    if (
        not profile_path.is_file()
        or archive.sha256_file(profile_path) != manifest["profile"]["sha256"]
    ):
        raise ReleaseError("release profile is missing or changed")
    profile = load_yaml(profile_path)
    validate(profile, PROFILE_SCHEMA, profile_path, root)
    if profile["id"] != manifest["profile"]["id"]:
        raise ReleaseError("release profile ID does not match the manifest")
    if profile["verification_commands"] != manifest["verification"]["commands"]:
        raise ReleaseError("release verification commands differ from the authoritative profile")
    fact_ids = profile.get("external_facts", [])
    if fact_ids != [fact["id"] for fact in manifest["external_facts"]]:
        raise ReleaseError("release external facts differ from the authoritative profile")
    facts = external_facts.refresh_and_compare(manifest["external_facts"], root)
    return profile, facts


def rebuild_and_compare(
    manifest: dict[str, Any], profile: dict[str, Any], artifact: Path, root: Path
) -> None:
    files = included_files(root, profile)
    if len(files) != manifest["artifact"]["file_count"]:
        raise ReleaseError("release artifact file count differs from the authoritative profile")
    with tempfile.TemporaryDirectory(prefix="release-rebuild-") as temporary:
        rebuilt = Path(temporary) / "artifact.zip"
        build_zip(root, files, rebuilt)
        if archive.sha256_file(rebuilt) != manifest["artifact"]["sha256"]:
            raise ReleaseError("release artifact does not match a clean rebuild from source")
    verify_artifact(
        artifact,
        profile["verification_commands"],
        profile.get("timeout_seconds", 300),
    )


def build_zip(root: Path, files: list[Path], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in files:
            info = zipfile.ZipInfo(path.relative_to(root).as_posix(), (1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            bundle.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED)


def verify_artifact(artifact: Path, commands: list[list[str]], timeout: int) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="release-verify-") as temporary:
        extract_root = Path(temporary)
        with zipfile.ZipFile(artifact) as bundle:
            for member in bundle.infolist():
                target = extract_root / member.filename
                try:
                    target.resolve().relative_to(extract_root.resolve())
                except ValueError as exc:
                    raise ReleaseError(
                        f"release archive path escapes extraction root: {member.filename}"
                    ) from exc
            bundle.extractall(extract_root)
        environment = {"PATH": os.environ.get("PATH", ""), "PYTHONUNBUFFERED": "1"}
        for command in commands:
            result = subprocess.run(
                command,
                cwd=extract_root,
                env=environment,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if result.returncode != 0:
                raise ReleaseError(
                    f"artifact-only verification failed ({' '.join(command)}): "
                    f"{result.stdout}{result.stderr}"
                )
    return {"commands": commands, "passed": True, "verified_at": archive.utc_now()}


def build_release(profile_path: Path, root: Path = ROOT, *, release_id: str | None = None) -> Path:
    try:
        relative_profile = profile_path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ReleaseError("release profile must be inside the repository") from exc
    profile = load_yaml(profile_path)
    validate(profile, PROFILE_SCHEMA, profile_path, root)
    files = included_files(root, profile)
    revision, dirty_hash = source_identity(root)
    identifier = (
        release_id
        or f"{archive.utc_now().replace(':', '').replace('-', '')}-{profile['id']}-{revision[:8]}"
    )
    if not RELEASE_ID_PATTERN.fullmatch(identifier):
        raise ReleaseError("release ID must use letters, digits, dots, underscores, or hyphens")
    release_root = managed_path(root, Path("dist") / identifier)
    if release_root.exists():
        raise ReleaseError(f"release destination already exists: {release_root}")
    release_root.mkdir(parents=True)
    artifact = managed_path(root, Path("dist") / identifier / "artifact.zip")
    build_zip(root, files, artifact)
    verification = verify_artifact(
        artifact, profile["verification_commands"], profile.get("timeout_seconds", 300)
    )
    fact_snapshots = external_facts.resolve_references(profile.get("external_facts", []), root)
    manifest = {
        "release_version": RELEASE_VERSION,
        "release_id": identifier,
        "created_at": archive.utc_now(),
        "profile": {
            "id": profile["id"],
            "path": relative_profile.as_posix(),
            "sha256": archive.sha256_file(profile_path),
        },
        "source": {"git_revision": revision, "dirty_state_sha256": dirty_hash},
        "artifact": {
            "path": str(artifact.relative_to(root)),
            "sha256": archive.sha256_file(artifact),
            "file_count": len(files),
        },
        "verification": verification,
        "external_facts": fact_snapshots,
        "release_ready": False,
        "approval": None,
    }
    manifest_path = managed_path(root, Path("dist") / identifier / "manifest.json")
    managed_path(root, Path("dist") / identifier / "manifest.json.tmp")
    validate(manifest, MANIFEST_SCHEMA, manifest_path, root)
    archive.write_json_atomic(manifest_path, manifest)
    return manifest_path


def verify_release(manifest_path: Path, root: Path = ROOT) -> dict[str, Any]:
    errors: list[str] = []
    identifier = "unknown"
    try:
        manifest = archive.read_json(manifest_path)
        validate(manifest, MANIFEST_SCHEMA, manifest_path, root)
        identifier = manifest["release_id"]
        _, artifact = release_layout(manifest_path, manifest, root)
        if not artifact.is_file():
            raise ReleaseError(f"release artifact is missing: {artifact}")
        if archive.sha256_file(artifact) != manifest["artifact"]["sha256"]:
            raise ReleaseError("release artifact checksum mismatch")
        profile, _ = authoritative_profile(manifest, root)
        rebuild_and_compare(manifest, profile, artifact, root)
    except (
        OSError,
        json.JSONDecodeError,
        ReleaseError,
        archive.ArchiveError,
        external_facts.ExternalFactError,
    ) as exc:
        errors.append(str(exc))
    return {"release_id": identifier, "valid": not errors, "errors": errors}


def record_release(
    manifest_path: Path,
    approved_by: str,
    expected_source_revision: str,
    root: Path = ROOT,
) -> tuple[Path, Path]:
    if not approved_by.strip():
        raise ReleaseError("approved-by identity must be non-empty")
    draft = archive.read_json(manifest_path)
    validate(draft, MANIFEST_SCHEMA, manifest_path, root)
    release_root, _ = release_layout(manifest_path, draft, root)
    if manifest_path.resolve() != release_root / "manifest.json":
        raise ReleaseError("strict recording requires the canonical draft manifest")
    approved_path = managed_path(
        root, Path("dist") / draft["release_id"] / "approved-manifest.json"
    )
    managed_path(root, Path("dist") / draft["release_id"] / "approved-manifest.json.tmp")
    provenance = managed_path(root, Path("releases") / f"{draft['release_id']}.md")
    if approved_path.exists():
        raise ReleaseError("approved release records are immutable and already exist")
    if draft.get("release_ready") is not False or draft.get("approval") is not None:
        raise ReleaseError("strict recording requires an unapproved draft manifest")
    if draft["source"]["dirty_state_sha256"] != CLEAN_STATE_SHA256:
        raise ReleaseError("strict release rejects artifacts built from a dirty source checkout")
    report = verify_release(manifest_path, root)
    if not report["valid"] or not draft["verification"]["passed"]:
        raise ReleaseError("draft release is not verified")
    _, facts = authoritative_profile(draft, root)
    external_facts.require_verified(facts, "strict release")
    current_revision, dirty_hash = source_identity(root)
    if (
        current_revision != expected_source_revision
        or draft["source"]["git_revision"] != current_revision
    ):
        raise ReleaseError("expected source revision does not match the draft and current checkout")
    if dirty_hash != CLEAN_STATE_SHA256:
        raise ReleaseError("strict release requires a clean source checkout")
    approved = {
        **draft,
        "release_ready": True,
        "approval": {
            "approved_by": approved_by,
            "approved_at": archive.utc_now(),
            "draft_manifest_sha256": archive.sha256_file(manifest_path),
        },
    }
    validate(approved, MANIFEST_SCHEMA, approved_path, root)
    provenance.parent.mkdir(parents=True, exist_ok=True)
    managed_path(root, Path("releases") / f"{draft['release_id']}.md")
    provenance_text = (
        f"# Release {draft['release_id']}\n\n"
        f"- Source revision: `{current_revision}`\n"
        f"- Artifact SHA-256: `{draft['artifact']['sha256']}`\n"
        f"- Draft manifest SHA-256: `{approved['approval']['draft_manifest_sha256']}`\n"
        f"- Approved by: `{approved_by}`\n"
        "- Release ready: `true`\n"
    )
    if provenance.exists() and provenance.read_text(encoding="utf-8") != provenance_text:
        raise ReleaseError("release provenance already exists with different content")
    if not provenance.exists():
        initialize = managed_path(root, Path("releases") / f"{draft['release_id']}.md.tmp")
        initialize.write_text(provenance_text, encoding="utf-8")
        os.replace(initialize, provenance)
    archive.write_json_atomic(approved_path, approved)
    return approved_path, provenance


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build and approve optional immutable releases.")
    sub = parser.add_subparsers(dest="command", required=True)
    validate_parser = sub.add_parser("validate")
    validate_parser.add_argument("profile", type=Path, nargs="?", default=DEFAULT_PROFILE)
    build = sub.add_parser("build")
    build.add_argument("profile", type=Path, nargs="?", default=DEFAULT_PROFILE)
    build.add_argument("--release-id")
    verify = sub.add_parser("verify")
    verify.add_argument("manifest", type=Path)
    record = sub.add_parser("record")
    record.add_argument("manifest", type=Path)
    record.add_argument("--approved-by", required=True)
    record.add_argument("--expected-source-revision", required=True)
    return parser


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "validate":
            profile = load_yaml(root / args.profile)
            validate(profile, PROFILE_SCHEMA, root / args.profile, root)
            included_files(root, profile)
            print(f"OK release profile {profile['id']}")
        elif args.command == "build":
            print(build_release(root / args.profile, root, release_id=args.release_id))
        elif args.command == "verify":
            report = verify_release(root / args.manifest, root)
            print(json.dumps(report, indent=2, sort_keys=True))
            return 0 if report["valid"] else 1
        else:
            approved, provenance = record_release(
                root / args.manifest, args.approved_by, args.expected_source_revision, root
            )
            print(f"{approved}\n{provenance}")
        return 0
    except (
        OSError,
        json.JSONDecodeError,
        ReleaseError,
        archive.ArchiveError,
        external_facts.ExternalFactError,
    ) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2
