"""Render Agent context for an Agent worktree."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path, PurePosixPath

from whub.services.errors import ServiceError
from whub.utils.managed_block import format_block


CONTEXT_MARKERS = (
    "<!-- whub:agent:context:start -->",
    "<!-- whub:agent:context:end -->",
)
HUB_AGENTS_PATH = "AGENTS.md"
HUB_SKILLS_PATH = ".agents/skills"
AGENTS_CONTEXT_PATH = PurePosixPath(".agents/AGENTS_context.md")
ROLE_ASSETS_PATH = ("assets", "roles")


@dataclass(frozen=True)
class AgentContext:
    """Agent context rendered for one worktree."""

    files: Mapping[PurePosixPath, str]
    blocks: Mapping[PurePosixPath, str]


def render_context(
    workspace_root: Path, role_names: Sequence[str] = (), branch: str | None = None
) -> AgentContext:
    """Snapshot Hub-owned Agent context without materializing it."""
    instructions = (
        "\n\n".join(
            instruction
            for instruction in (
                _hub_agents_instructions(workspace_root),
                _role_instructions(role_names),
                (
                    f"# Session context\n\n- Registered branch: `{branch}`"
                    if branch is not None
                    else ""
                ),
            )
            if instruction
        )
        + "\n"
    )
    return AgentContext(
        {
            **_hub_skill_files(workspace_root),
            AGENTS_CONTEXT_PATH: instructions,
        },
        {
            PurePosixPath(HUB_AGENTS_PATH): format_block(
                CONTEXT_MARKERS, f"@{AGENTS_CONTEXT_PATH}\n"
            ),
            PurePosixPath(".claude/CLAUDE.md"): format_block(
                CONTEXT_MARKERS, "@../AGENTS.md"
            ),
        },
    )


def _hub_agents_instructions(workspace_root: Path) -> str:
    rules = workspace_root / HUB_AGENTS_PATH
    if not rules.is_file():
        return ""
    return (
        "# Hub common rules\n"
        f"Relative paths in this document are relative to Hub root: {workspace_root}\n\n"
        f"{rules.read_text().rstrip()}"
    )


def _hub_skill_files(workspace_root: Path) -> dict[PurePosixPath, str]:
    root = workspace_root / HUB_SKILLS_PATH
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


def _role_instructions(role_names: Sequence[str]) -> str:
    assets = files("whub").joinpath(*ROLE_ASSETS_PATH)
    paths = [assets / "base.md"]
    for name in role_names:
        if Path(name).name != name:
            raise ServiceError(f"invalid Agent role name: {name}")
        paths.append(assets / name / "description.md")

    contents: list[str] = []
    for path in paths:
        if not path.is_file():
            raise ServiceError(f"Agent role instructions are missing: {path}")
        try:
            contents.append(path.read_text().rstrip())
        except OSError as error:
            raise ServiceError(
                f"failed to read Agent role instructions: {path}"
            ) from error
    return "\n\n".join(contents) + "\n"
