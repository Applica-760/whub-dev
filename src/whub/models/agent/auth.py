"""Models for reusable Agent authorization assets."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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


# ── Approval ───────────────────────────────────────────────────────────────────────────────
class ApprovalPolicy(StrEnum):
    REQUEST = "request"
    NEVER = "never"


class ApprovalReviewer(StrEnum):
    USER = "user"
    AUTO_REVIEW = "auto_review"


class ApprovalGrants(AgentAuthModel):
    policy: ApprovalPolicy = ApprovalPolicy.REQUEST
    reviewer: ApprovalReviewer = ApprovalReviewer.USER


# ── Extension tools ─────────────────────────────────────────────────────────
class ExtensionToolError(ValueError):
    """Raised when a registered extension tool cannot be loaded."""


ExtensionToolId = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*$")]


class ExtensionTool(AgentAuthModel):
    """One Hub-managed external tool that an Agent auth may grant."""

    id: ExtensionToolId
    protocol: Literal["mcp"]
    transport: Literal["stdio"]
    command: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._+/-]*$")
    args: list[str] = Field(default_factory=list)
    tools: list[str] = Field(min_length=1)

    @field_validator("args")
    @classmethod
    def _validate_args(cls, value: list[str]) -> list[str]:
        if any(not argument for argument in value):
            raise ValueError("extension tool arguments must not be empty")
        return value

    @field_validator("tools")
    @classmethod
    def _validate_tools(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("extension tool names must be unique")
        return value


class ExtensionToolCatalog(AgentAuthModel):
    """All extension tools registered in one Hub."""

    tools: list[ExtensionTool]

    @model_validator(mode="after")
    def _validate_unique_ids(self) -> ExtensionToolCatalog:
        ids = [tool.id for tool in self.tools]
        if len(ids) != len(set(ids)):
            raise ValueError("extension tool IDs must be unique")
        return self


# ── Role ───────────────────────────────────────────────────────────────────────────────────
class Grants(AgentAuthModel):
    commands: CommandGrants
    filesystem: FilesystemGrants
    network: NetworkGrants
    approval: ApprovalGrants = Field(default_factory=ApprovalGrants)
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


class EffectiveAuth(AgentAuthModel):
    """Authorization grants composed from one base and extension auths."""

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


def load_extension_tool(directory: Path) -> ExtensionToolCatalog:
    """Load all registered extension tool assets in one directory."""
    try:
        data = [
            yaml.safe_load(path.read_text())
            for path in sorted(directory.glob("*.yaml"))
        ]
        return ExtensionToolCatalog.model_validate({"tools": data})
    except (OSError, UnicodeError, yaml.YAMLError, ValueError) as error:
        raise ExtensionToolError(
            f"invalid extension tool catalog: {directory}"
        ) from error
