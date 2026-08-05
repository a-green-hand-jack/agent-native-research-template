from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from jsonschema import Draft202012Validator

from . import initialize_project

ROOT = Path(__file__).resolve().parents[1]
PLAN_VERSION = 1
PLAN_SCHEMA = Path("schemas/template-plan.schema.json")


class TemplateLifecycleError(ValueError):
    """Raised when a template lifecycle plan or transition is unsafe."""


def git(root: Path, *arguments: str, text: bool = True) -> str | bytes:
    result = subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=False,
        capture_output=True,
        text=text,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() if text else result.stderr.decode(errors="replace").strip()
        raise TemplateLifecycleError(f"git {' '.join(arguments)} failed: {detail}")
    return result.stdout.strip() if text else result.stdout


def repository_name(root: Path) -> str:
    try:
        value = str(git(root, "remote", "get-url", "origin"))
    except TemplateLifecycleError:
        return str(root.resolve())
    parsed = urlsplit(value)
    if parsed.scheme and parsed.hostname:
        host = parsed.hostname
        if parsed.port is not None:
            host = f"{host}:{parsed.port}"
        return urlunsplit((parsed.scheme, host, parsed.path, parsed.query, parsed.fragment))
    return value


def commit(root: Path, revision: str = "HEAD") -> str:
    return str(git(root, "rev-parse", "--verify", f"{revision}^{{commit}}"))


def file_at(root: Path, revision: str, relative: str) -> bytes | None:
    result = subprocess.run(
        ["git", "show", f"{revision}:{relative}"],
        cwd=root,
        check=False,
        capture_output=True,
    )
    if result.returncode == 0:
        return result.stdout
    return None


def safe_working_path(root: Path, relative: str) -> Path:
    path = root
    for part in Path(relative).parts:
        path = path / part
        if path.is_symlink():
            raise TemplateLifecycleError(f"downstream path contains symbolic link: {relative}")
    try:
        path.resolve(strict=False).relative_to(root.resolve())
    except ValueError as exc:
        raise TemplateLifecycleError(f"downstream path escapes repository: {relative}") from exc
    return path


def working_file(root: Path, relative: str) -> bytes | None:
    path = safe_working_path(root, relative)
    if path.is_file() and not path.is_symlink():
        return path.read_bytes()
    return None


def canonical_sha256(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def changed_paths(template_root: Path, baseline: str, target: str) -> list[tuple[str, str]]:
    result = subprocess.run(
        ["git", "diff", "--name-status", "-z", "--no-renames", baseline, target],
        cwd=template_root,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise TemplateLifecycleError(
            f"git diff failed: {result.stderr.decode(errors='replace').strip()}"
        )
    changes: list[tuple[str, str]] = []
    fields = [field for field in result.stdout.split(b"\0") if field]
    if len(fields) % 2:
        raise TemplateLifecycleError("git diff returned an incomplete name-status record")
    for index in range(0, len(fields), 2):
        changes.append((fields[index].decode(), os.fsdecode(fields[index + 1])))
    return changes


def classify_change(
    downstream_root: Path,
    template_root: Path,
    baseline: str | None,
    target: str,
    status: str,
    relative: str,
) -> dict[str, str]:
    before = file_at(template_root, baseline, relative) if baseline else None
    after = file_at(template_root, target, relative)
    current = working_file(downstream_root, relative)
    upstream_change = {"A": "added", "M": "modified", "D": "deleted"}.get(status, "present")
    ownership = (
        "not-present"
        if current is None
        else "template-owned"
        if before is not None and current == before
        else "shared/customized"
    )
    if current == after:
        disposition, operation = "already", "noop"
    elif baseline is None:
        disposition, operation = "manual", "review"
    elif after is None:
        disposition, operation = "manual", "delete"
    elif current == before or (before is None and current is None):
        disposition, operation = "safe", "write"
    else:
        disposition, operation = "conflict", "review"
    return {
        "path": relative,
        "upstream_change": upstream_change,
        "ownership": ownership,
        "disposition": disposition,
        "operation": operation,
    }


def validate_plan(plan: dict[str, Any], root: Path) -> None:
    schema = json.loads((root / PLAN_SCHEMA).read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(plan),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.absolute_path) or "$"
        raise TemplateLifecycleError(f"template plan schema error at {location}: {error.message}")
    payload = {key: value for key, value in plan.items() if key != "plan_sha256"}
    if plan["plan_sha256"] != canonical_sha256(payload):
        raise TemplateLifecycleError("template plan hash does not match its canonical content")
    for entry in plan["changes"]:
        path = Path(entry["path"])
        if path.is_absolute() or ".." in path.parts:
            raise TemplateLifecycleError(f"template plan path must be repository-relative: {path}")


def validate_plan_source(plan: dict[str, Any], template_root: Path) -> None:
    if plan["template"]["repository"] != repository_name(template_root):
        raise TemplateLifecycleError("template plan repository does not match --template-root")


def inspect(root: Path = ROOT) -> dict[str, Any]:
    state = initialize_project.load_yaml(root / initialize_project.STATE_PATH)
    return {
        "project": state,
        "git": {
            "commit": commit(root),
            "branch": str(git(root, "branch", "--show-current")),
            "dirty": bool(str(git(root, "status", "--porcelain=v1", "--untracked-files=all"))),
        },
    }


def create_plan(
    downstream_root: Path,
    template_root: Path,
    target_revision: str,
    *,
    mode: str = "auto",
) -> dict[str, Any]:
    state_path = downstream_root / initialize_project.STATE_PATH
    state = (
        initialize_project.load_yaml(state_path) if state_path.is_file() else {"initialized": False}
    )
    metadata = state.get("template", {})
    resolved_mode = "update" if state.get("initialized") is True else "adoption"
    if mode != "auto" and mode != resolved_mode:
        raise TemplateLifecycleError(
            f"requested mode {mode!r} does not match repository state {resolved_mode!r}"
        )
    baseline = metadata.get("reviewed_template_commit") if resolved_mode == "update" else None
    if resolved_mode == "update" and not isinstance(baseline, str):
        raise TemplateLifecycleError("initialized project has no reviewed template baseline")
    target = commit(template_root, target_revision)
    if baseline:
        baseline = commit(template_root, baseline)
        paths = changed_paths(template_root, baseline, target)
    else:
        result = subprocess.run(
            ["git", "ls-tree", "-rz", "--name-only", target],
            cwd=template_root,
            check=False,
            capture_output=True,
        )
        if result.returncode != 0:
            raise TemplateLifecycleError(
                f"git ls-tree failed: {result.stderr.decode(errors='replace').strip()}"
            )
        paths = [("P", os.fsdecode(path)) for path in result.stdout.split(b"\0") if path]
    changes = [
        classify_change(downstream_root, template_root, baseline, target, status, relative)
        for status, relative in paths
    ]
    payload: dict[str, Any] = {
        "plan_version": PLAN_VERSION,
        "mode": resolved_mode,
        "template": {
            "repository": repository_name(template_root),
            "baseline_commit": baseline,
            "target_commit": target,
        },
        "downstream": {
            "commit": commit(downstream_root),
            "dirty": bool(
                str(git(downstream_root, "status", "--porcelain=v1", "--untracked-files=all"))
            ),
        },
        "changes": changes,
    }
    plan = {**payload, "plan_sha256": canonical_sha256(payload)}
    validate_plan(plan, template_root)
    return plan


def require_apply_branch(root: Path) -> None:
    if str(git(root, "status", "--porcelain=v1", "--untracked-files=all")):
        raise TemplateLifecycleError("template apply requires a clean downstream worktree")
    branch = str(git(root, "branch", "--show-current"))
    default_branches = {"main", "master"}
    result = subprocess.run(
        ["git", "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0 and result.stdout.strip().startswith("origin/"):
        default_branches.add(result.stdout.strip().removeprefix("origin/"))
    if not branch or branch in default_branches:
        raise TemplateLifecycleError("template apply requires a non-default branch")


def apply_plan(
    plan: dict[str, Any], downstream_root: Path, template_root: Path, expected_sha256: str
) -> list[str]:
    validate_plan(plan, template_root)
    validate_plan_source(plan, template_root)
    if plan["plan_sha256"] != expected_sha256:
        raise TemplateLifecycleError("expected plan hash does not match")
    if plan["mode"] != "update":
        raise TemplateLifecycleError(
            "automatic apply is available only for provenance-backed updates"
        )
    require_apply_branch(downstream_root)
    fresh = create_plan(downstream_root, template_root, plan["template"]["target_commit"])
    if fresh != plan:
        raise TemplateLifecycleError(
            "template plan is stale or does not match current repositories"
        )
    target = commit(template_root, plan["template"]["target_commit"])
    changes: list[str] = []
    for entry in plan["changes"]:
        if entry["disposition"] != "safe" or entry["operation"] != "write":
            continue
        content = file_at(template_root, target, entry["path"])
        if content is None:
            raise TemplateLifecycleError(f"target content is missing for {entry['path']}")
        path = safe_working_path(downstream_root, entry["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        safe_working_path(downstream_root, entry["path"])
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_bytes(content)
        os.replace(temporary, path)
        changes.append(f"write {entry['path']}")
    return changes


def record_baseline(
    plan: dict[str, Any], downstream_root: Path, template_root: Path, expected_sha256: str
) -> None:
    validate_plan(plan, template_root)
    validate_plan_source(plan, template_root)
    if plan["plan_sha256"] != expected_sha256:
        raise TemplateLifecycleError("expected plan hash does not match")
    if plan["mode"] != "update":
        raise TemplateLifecycleError("baseline recording requires a provenance-backed update plan")
    state = initialize_project.load_yaml(downstream_root / initialize_project.STATE_PATH)
    if state["template"].get("reviewed_template_commit") != plan["template"]["baseline_commit"]:
        raise TemplateLifecycleError("reviewed template baseline changed after planning")
    if commit(downstream_root) != plan["downstream"]["commit"]:
        raise TemplateLifecycleError("downstream HEAD changed after planning")
    target = commit(template_root, plan["template"]["target_commit"])
    expected_paths = {
        relative
        for _, relative in changed_paths(template_root, plan["template"]["baseline_commit"], target)
    }
    if {entry["path"] for entry in plan["changes"]} != expected_paths:
        raise TemplateLifecycleError("template plan path set does not match the upstream diff")
    for entry in plan["changes"]:
        expected = file_at(template_root, target, entry["path"])
        current = working_file(downstream_root, entry["path"])
        if expected != current:
            raise TemplateLifecycleError(
                f"cannot record baseline before resolving target path: {entry['path']}"
            )
    state["template"]["reviewed_template_commit"] = target
    initialize_project.write_text(
        downstream_root / initialize_project.STATE_PATH, initialize_project.dump_yaml(state)
    )


def read_plan(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TemplateLifecycleError("template plan must be a JSON object")
    return value


def write_plan(path: Path, plan: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect and apply reviewed template lifecycle plans."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("inspect")
    plan = sub.add_parser("plan")
    plan.add_argument("--template-root", type=Path, required=True)
    plan.add_argument("--target", required=True)
    plan.add_argument("--mode", choices=["auto", "adoption", "update"], default="auto")
    plan.add_argument("--output", type=Path)
    for name in ("apply", "record-baseline"):
        action = sub.add_parser(name)
        action.add_argument("plan", type=Path)
        action.add_argument("--template-root", type=Path, required=True)
        action.add_argument("--expected-plan-sha256", required=True)
    return parser


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "inspect":
            print(json.dumps(inspect(root), indent=2, sort_keys=True))
        elif args.command == "plan":
            plan = create_plan(root, args.template_root.resolve(), args.target, mode=args.mode)
            if args.output:
                write_plan(args.output, plan)
                print(args.output)
            else:
                print(json.dumps(plan, indent=2, sort_keys=True))
        elif args.command == "apply":
            changes = apply_plan(
                read_plan(args.plan), root, args.template_root.resolve(), args.expected_plan_sha256
            )
            print("\n".join(changes) if changes else "OK no safe writes required")
        else:
            record_baseline(
                read_plan(args.plan), root, args.template_root.resolve(), args.expected_plan_sha256
            )
            print("OK reviewed template baseline recorded")
        return 0
    except (
        OSError,
        json.JSONDecodeError,
        TemplateLifecycleError,
        initialize_project.InitializationError,
    ) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2
