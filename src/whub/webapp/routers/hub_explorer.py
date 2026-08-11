"""Hub Explorer JSON API."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from whub.core.context import current_context
from whub.services.hub_explorer import (
    HubEntry,
    HubFile,
    list_hub_directory,
    read_hub_file,
)


router = APIRouter(prefix="/api/hub-explorer")


class HubDirectoryResponse(BaseModel):
    entries: list[HubEntry]


@router.get("/directory", response_model=HubDirectoryResponse)
def get_hub_directory(path: str = "") -> HubDirectoryResponse:
    return HubDirectoryResponse(
        entries=list_hub_directory(current_context().workspace_root, path)
    )


@router.get("/file", response_model=HubFile)
def get_hub_file(path: str) -> HubFile:
    return read_hub_file(current_context().workspace_root, path)
