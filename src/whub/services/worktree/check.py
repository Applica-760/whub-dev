"""Git consistency checks for registered worktrees."""

from __future__ import annotations

from pathlib import Path

from whub.models import (
    GitWorktree,
    Manifest,
    WorktreeDefinitionRecord,
    WorktreeInspection,
)
from whub.services.errors import ServiceError
from whub.services.worktree.definition import list_worktree_definitions
from whub.services.worktree.git import process_detail, run_git
from whub.services.worktree.resolve import resolve_worktree_parent


def inspect_worktrees(
    manifest: Manifest, workspace_root: Path
) -> list[WorktreeInspection]:
    """Inspect registered definitions without modifying Git or YAML state."""
    return [
        _inspect_worktree(manifest, workspace_root, record)
        for record in list_worktree_definitions(workspace_root)
    ]


def _inspect_worktree(
    manifest: Manifest, workspace_root: Path, record: WorktreeDefinitionRecord
) -> WorktreeInspection:
    diagnostics = list(record.diagnostics)
    definition = record.definition
    if definition is None or diagnostics:
        return WorktreeInspection(record, tuple(diagnostics))
    try:
        worktrees = _list_git_worktrees(resolve_worktree_parent(manifest, definition))
    except ServiceError as error:
        diagnostics.append(str(error))
        return WorktreeInspection(record, tuple(diagnostics))
    git_worktree = next(
        (
            item
            for item in worktrees
            if item.path == workspace_root / definition.workspace_path
        ),
        None,
    )
    if git_worktree is None:
        diagnostics.append(f"git worktree is missing: {definition.workspace_path}")
    elif git_worktree.branch != f"refs/heads/{definition.branch}":
        found = (
            git_worktree.branch.removeprefix("refs/heads/")
            if git_worktree.branch is not None
            else "detached HEAD"
        )
        diagnostics.append(
            "git worktree branch does not match definition: "
            f"expected {definition.branch}, found {found}"
        )
    return WorktreeInspection(record, tuple(diagnostics))


def _list_git_worktrees(parent: Path) -> list[GitWorktree]:
    result = run_git(parent, "worktree", "list", "--porcelain")
    if result.returncode != 0:
        raise ServiceError("git worktree list failed: " + process_detail(result))
    return _parse_git_worktrees(result.stdout)


def _parse_git_worktrees(output: str) -> list[GitWorktree]:
    worktrees: list[GitWorktree] = []
    fields: dict[str, str] = {}
    for line in [*output.splitlines(), ""]:
        if line:
            key, _, value = line.partition(" ")
            fields[key] = value
            continue
        if "worktree" in fields:
            worktrees.append(
                GitWorktree(path=Path(fields["worktree"]), branch=fields.get("branch"))
            )
        fields = {}
    return worktrees
