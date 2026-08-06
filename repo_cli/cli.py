from __future__ import annotations

import sys
from pathlib import Path

from . import describe, project

PROJECT_FILE = "PROJECT.yaml"
REPO_CLI_NAME = "repoctl"


class RepoCLIError(ValueError):
    """Raised when the repository CLI cannot resolve or dispatch a command."""


def find_project_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / PROJECT_FILE).is_file():
            return candidate
    raise RepoCLIError(
        f"cannot find {PROJECT_FILE} from {current}; run repoctl inside a project repository"
    )


def render_help() -> str:
    return (
        "usage: repoctl <command> [arguments]\n\n"
        "Repository-development interface.\n\n"
        "commands:\n"
        "  describe    print repository and project interfaces; use --json for agents\n"
        "  check       validate project identity and retained repository surfaces\n\n"
        "Project and research workloads remain on the project CLI declared in PROJECT.yaml.\n"
    )


def main(argv: list[str] | None = None, root: Path | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    try:
        repository_root = root.resolve() if root is not None else find_project_root()
        if not arguments or arguments[0] in {"-h", "--help"}:
            print(render_help(), end="")
            return 0
        command, *command_arguments = arguments
        if command == "describe":
            return describe.main(command_arguments, repository_root)
        if command == "check":
            if command_arguments:
                raise RepoCLIError("repoctl check accepts no arguments")
            return project.main(["check"], repository_root)
        raise RepoCLIError(f"unknown command {command!r}; expected describe or check")
    except RepoCLIError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
