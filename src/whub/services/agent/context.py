"""Render Agent context for an Agent worktree."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from whub.services.errors import ServiceError
from whub.utils.managed_block import format_block


CONTEXT_MARKERS = (
    "<!-- whub:agent:context:start -->",
    "<!-- whub:agent:context:end -->",
)
HUB_AGENTS_PATH = "AGENTS.md"
HUB_SKILLS_PATH = ".agents/skills"


@dataclass(frozen=True)
class AgentContext:
    """Agent context rendered for one worktree."""

    files: Mapping[PurePosixPath, str]
    blocks: Mapping[PurePosixPath, str]


def render_context(workspace_root: Path) -> AgentContext:
    """Snapshot Hub-owned Agent context without materializing it."""
    rules = workspace_root / HUB_AGENTS_PATH
    if not rules.is_file():
        return AgentContext({}, {})
    return AgentContext(
        _skill_files(workspace_root / HUB_SKILLS_PATH),
        {
            PurePosixPath(HUB_AGENTS_PATH): format_block(
                CONTEXT_MARKERS,
                "# Hub common rules\n"
                f"Relative paths in this block are relative to Hub root: {workspace_root}\n\n"
                f"{rules.read_text().rstrip()}\n",
            ),
            PurePosixPath(".claude/CLAUDE.md"): format_block(
                CONTEXT_MARKERS, "@../AGENTS.md"
            ),
        },
    )


def _skill_files(root: Path) -> dict[PurePosixPath, str]:
    if not root.exists():
        return {}
    if not root.is_dir() or root.is_symlink():
        raise ServiceError(f"Hub Skills directory is invalid: {root}")
    files: dict[PurePosixPath, str] = {}
    for source in sorted(root.rglob("*")):
        if source.is_dir():
            continue
        if source.is_symlink() or not source.is_file():
            raise ServiceError(f"Hub Skill is not a regular file: {source}")
        files[PurePosixPath(HUB_SKILLS_PATH) / source.relative_to(root)] = (
            source.read_text()
        )
    return files
