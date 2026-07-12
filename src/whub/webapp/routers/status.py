"""Resource status JSON API."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from whub.core.health import HealthState
from whub.models import load_manifest
from whub.services.status import collect_resource_status


router = APIRouter(prefix="/api/resources")


class ResourceStatusResponse(BaseModel):
    project: str
    state: HealthState
    type: Literal["symlink", "remote"]
    mount: str
    tmux: str
    git: str


class ResourceStatusListResponse(BaseModel):
    resources: list[ResourceStatusResponse]


@router.get("/status", response_model=ResourceStatusListResponse)
def get_resource_status() -> ResourceStatusListResponse:
    return ResourceStatusListResponse(
        resources=[
            ResourceStatusResponse(
                project=item.project,
                state=item.state,
                type=item.type,
                mount=item.mount,
                tmux=item.tmux,
                git=item.git,
            )
            for item in collect_resource_status(load_manifest())
        ],
    )
