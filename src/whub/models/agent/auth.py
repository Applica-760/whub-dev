"""Models for reusable Agent authorization assets."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from whub.models.agent.extension_tool import ExtensionToolId


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
class LiteralValue(AgentAuthModel):
    kind: Literal["literal"] = "literal"
    value: str = Field(min_length=1)


class VariableReference(AgentAuthModel):
    kind: Literal["variable"] = "variable"
    name: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$")


CommandToken = Annotated[
    LiteralValue | VariableReference,
    Field(discriminator="kind"),
]


def _parse_command_token(value: str | dict[str, str]) -> dict[str, str]:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        raise ValueError("command value must be a string")
    if value.startswith("$"):
        return {"kind": "variable", "name": value[1:]}
    return {"kind": "literal", "value": value}


class CommandRule(AgentAuthModel):
    executable: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")
    arguments: list[CommandToken] = Field(default_factory=list)

    @field_validator("arguments", mode="before")
    @classmethod
    def _parse_tokens(cls, value: list[str | dict[str, str]]) -> list[dict[str, str]]:
        return [_parse_command_token(token) for token in value]


class CommandGrants(AgentAuthModel):
    prefixes: list[CommandRule]
    exact: list[CommandRule]


# ── Filesystem ─────────────────────────────────────────────────────────────────────────────
FilesystemScope = Literal["hub_logical_tree", "current_worktree"]


class FilesystemGrants(AgentAuthModel):
    read: list[FilesystemScope] = Field(default_factory=list)
    write: list[FilesystemScope] = Field(default_factory=list)

    @field_validator("read", "write")
    @classmethod
    def _validate_unique_scopes(
        cls, value: list[FilesystemScope]
    ) -> list[FilesystemScope]:
        if len(value) != len(set(value)):
            raise ValueError("filesystem scopes must be unique")
        return value


# ── Network ────────────────────────────────────────────────────────────────────────────────
class NetworkPolicy(StrEnum):
    DENY_ALL = "deny_all"


class NetworkGrants(AgentAuthModel):
    policy: NetworkPolicy


# ── Role ───────────────────────────────────────────────────────────────────────────────────
class Grants(AgentAuthModel):
    commands: CommandGrants
    filesystem: FilesystemGrants
    network: NetworkGrants
    extension_tools: list[ExtensionToolId]

    @field_validator("extension_tools")
    @classmethod
    def _validate_unique_extension_tools(
        cls, value: list[ExtensionToolId]
    ) -> list[ExtensionToolId]:
        if len(value) != len(set(value)):
            raise ValueError("extension tools must be unique")
        return value


class AgentAuth(AgentAuthModel):
    name: str = Field(min_length=1)
    type: Literal["base", "extension"]
    variables: dict[str, VariableDefinition]
    grants: Grants

    @model_validator(mode="after")
    def _validate_command_variables(self) -> AgentAuth:
        rules = [*self.grants.commands.prefixes, *self.grants.commands.exact]
        for rule in rules:
            for token in rule.arguments:
                if isinstance(token, VariableReference):
                    self._validate_variable_reference(token.name)
        return self

    def _validate_variable_reference(self, reference: str) -> None:
        root, *fields = reference.split(".")
        variable = self.variables.get(root)
        if variable is None:
            raise ValueError(f"unknown command variable: ${reference}")
        if isinstance(variable, RegisteredProjectVariable):
            if fields:
                raise ValueError(f"variable does not expose fields: ${reference}")
            return
        if len(fields) != 1 or fields[0] not in variable.fields:
            raise ValueError(f"invalid command variable reference: ${reference}")


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
