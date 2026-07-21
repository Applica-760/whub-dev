"""Project JSON API."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from whub.models import load_manifest


router = APIRouter(prefix="/api/projects")


class ProjectsResponse(BaseModel):
    projects: list[str]


@router.get("", response_model=ProjectsResponse)
def get_projects() -> ProjectsResponse:
    return ProjectsResponse(
        projects=[project.name for project in load_manifest().projects]
    )
