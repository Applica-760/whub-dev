"""Knowledge JSON API."""

from __future__ import annotations

from fastapi import APIRouter

from whub.models import Knowledge, load_manifest
from whub.services.knowledge import load_project_knowledge


router = APIRouter(prefix="/api/knowledge")


@router.get("/{project}", response_model=Knowledge)
def get_knowledge(project: str) -> Knowledge:
    return load_project_knowledge(load_manifest(), project)
