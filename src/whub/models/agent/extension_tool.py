"""Models for Hub-registered extension tools."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ExtensionToolError(ValueError):
    """Raised when a registered extension tool cannot be loaded."""


ExtensionToolId = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]*$")]


class ExtensionTool(BaseModel):
    """One Hub-managed external tool that a Role may be granted."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: ExtensionToolId
    protocol: Literal["mcp"]
    transport: Literal["stdio"]
    tools: list[str] = Field(min_length=1)

    @field_validator("tools")
    @classmethod
    def _validate_tools(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("extension tool names must be unique")
        return value


class ExtensionToolCatalog(BaseModel):
    """All extension tools registered in one Hub."""

    model_config = ConfigDict(extra="forbid")

    tools: list[ExtensionTool]

    @model_validator(mode="after")
    def _validate_unique_ids(self) -> ExtensionToolCatalog:
        ids = [tool.id for tool in self.tools]
        if len(ids) != len(set(ids)):
            raise ValueError("extension tool IDs must be unique")
        return self


def load_extension_tool_catalog(directory: Path) -> ExtensionToolCatalog:
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
