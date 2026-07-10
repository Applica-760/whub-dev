"""Inbox JSON API."""
from __future__ import annotations

from fastapi import APIRouter, status
from pydantic import BaseModel

from whub.models import load_manifest
from whub.services.inbox import create_inbox_note


router = APIRouter(prefix="/api/inbox")


class CreateInboxRequest(BaseModel):
    title: str
    body: str


class InboxResponse(BaseModel):
    filename: str


@router.post("", response_model=InboxResponse, status_code=status.HTTP_201_CREATED)
def create_inbox(request: CreateInboxRequest) -> InboxResponse:
    path = create_inbox_note(load_manifest(), request.title, request.body)
    return InboxResponse(filename=path.name)
