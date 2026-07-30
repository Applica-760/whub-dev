"""Models for reusable Agent authorization assets."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


Argv = Annotated[list[str], Field(min_length=1)]


class AgentAuthError(ValueError):
    """Raised when an Agent authorization asset cannot be loaded."""


class AgentAuthModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


# ── Variables ──────────────────────────────────────────────────────────────────────────────
class RegisteredProjectVariable(AgentAuthModel):
    source: Literal["registered_project"]


class RegisteredTaskWorktreeVariable(AgentAuthModel):
    source: Literal["registered_task_worktree"]
    fields: list[Literal["project", "task", "path"]] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_fields(self) -> RegisteredTaskWorktreeVariable:
        if len(self.fields) != len(set(self.fields)):
            raise ValueError("variable fields must be unique")
        return self


VariableDefinition = Annotated[
    RegisteredProjectVariable | RegisteredTaskWorktreeVariable,
    Field(discriminator="source"),
]


# ── Commands ───────────────────────────────────────────────────────────────────────────────
class VariableExactCommand(AgentAuthModel):
    mode: Literal["exact"]
    argv: Argv


class VariablePrefixCommand(AgentAuthModel):
    mode: Literal["prefix"]
    argv: Argv


VariableCommand = Annotated[
    VariableExactCommand | VariablePrefixCommand,
    Field(discriminator="mode"),
]


class CommandGrants(AgentAuthModel):
    prefixes: list[Argv]
    exact: list[Argv]
    templates: list[VariableCommand]


# ── Filesystem ─────────────────────────────────────────────────────────────────────────────
class FilesystemGrant(AgentAuthModel):
    scope: str = Field(min_length=1)
    access: Literal["read", "write"]


# ── Network ────────────────────────────────────────────────────────────────────────────────
class NetworkGrants(AgentAuthModel):
    outbound: list[str]


# ── External tools ─────────────────────────────────────────────────────────────────────────
class ExternalToolGrant(AgentAuthModel):
    name: str = Field(min_length=1)
    transport: Literal["stdio"]
    tools: list[str]


# ── Role ───────────────────────────────────────────────────────────────────────────────────
class Grants(AgentAuthModel):
    commands: CommandGrants
    filesystem: list[FilesystemGrant]
    network: NetworkGrants
    external_tools: list[ExternalToolGrant]


class AgentAuth(AgentAuthModel):
    name: str = Field(min_length=1)
    type: Literal["base", "extension"]
    variables: dict[str, VariableDefinition]
    grants: Grants


def load_agent_auth(path: Path) -> AgentAuth:
    """Load and validate one `agent-auth.yaml` or `base.yaml` asset."""
    try:
        data = yaml.safe_load(path.read_text())
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise AgentAuthError(f"invalid agent auth asset: {path}") from error
    try:
        return AgentAuth.model_validate(data)
    except ValueError as error:
        raise AgentAuthError(f"invalid agent auth asset: {path}: {error}") from error
