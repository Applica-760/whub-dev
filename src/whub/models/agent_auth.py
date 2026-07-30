"""Models for reusable Agent authorization assets."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from whub.models.extension_tool import (
    ExtensionTool,
    ExtensionToolCatalog,
    ExtensionToolId,
)


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


CommandValue = Annotated[
    LiteralValue | VariableReference,
    Field(discriminator="kind"),
]


def _parse_command_value(value: str | dict[str, str]) -> dict[str, str]:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        raise ValueError("command value must be a string")
    if value.startswith("$"):
        return {"kind": "variable", "name": value[1:]}
    return {"kind": "literal", "value": value}


class PositionalArgument(AgentAuthModel):
    positional: CommandValue

    @field_validator("positional", mode="before")
    @classmethod
    def _parse_value(cls, value: str | dict[str, str]) -> dict[str, str]:
        return _parse_command_value(value)


class CommandOption(AgentAuthModel):
    name: str = Field(pattern=r"^-{1,2}[A-Za-z0-9][A-Za-z0-9_-]*$")
    value: CommandValue | None = None

    @field_validator("value", mode="before")
    @classmethod
    def _parse_value(cls, value: str | dict[str, str] | None) -> dict[str, str] | None:
        return _parse_command_value(value) if value is not None else None


class OptionArgument(AgentAuthModel):
    option: CommandOption


CommandArgument = PositionalArgument | OptionArgument


class CommandRule(AgentAuthModel):
    executable: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")
    arguments: list[CommandArgument] = Field(default_factory=list)


class PrefixCommandRule(CommandRule):
    """Allow argv whose initial tokens match this rule."""


class ExactCommandRule(CommandRule):
    """Allow only argv whose complete tokens match this rule."""


class CommandGrants(AgentAuthModel):
    prefixes: list[PrefixCommandRule]
    exact: list[ExactCommandRule]


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
class NetworkGrants(AgentAuthModel):
    """No network access is granted."""


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
            for argument in rule.arguments:
                value = (
                    argument.positional
                    if isinstance(argument, PositionalArgument)
                    else argument.option.value
                )
                if isinstance(value, VariableReference):
                    self._validate_variable_reference(value.name)
        return self

    def resolve_extension_tools(
        self, catalog: ExtensionToolCatalog
    ) -> list[ExtensionTool]:
        """Resolve this Role's extension-tool IDs against the Hub catalog."""
        return catalog.resolve(self.grants.extension_tools)

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
