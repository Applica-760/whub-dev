"""Backlog JSON API."""
from __future__ import annotations

from fastapi import APIRouter, Response, status
from pydantic import BaseModel, field_validator

from whub.models import load_manifest
from whub.services.backlog import append_backlog, read_backlog


router = APIRouter(prefix="/api/backlog")


class BacklogResponse(BaseModel):
    project: str
    content: str


class CreateBacklogRequest(BaseModel):
    memo: str

    @field_validator("memo")
    @classmethod
    def _validate_memo(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("memo must not be blank")
        return normalized


@router.get("/{project}", response_model=BacklogResponse)
def get_backlog(project: str) -> BacklogResponse:
    return BacklogResponse(
        project=project,
        content=read_backlog(load_manifest(), project),
    )


@router.post("/{project}", status_code=status.HTTP_201_CREATED)
def create_backlog_memo(project: str, request: CreateBacklogRequest) -> Response:
    append_backlog(load_manifest(), project, request.memo)
    return Response(status_code=status.HTTP_201_CREATED)
