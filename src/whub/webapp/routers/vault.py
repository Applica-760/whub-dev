"""Vault JSON API."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from whub.models import load_manifest
from whub.services.vault import VaultNode, list_vault_tree, read_vault_note


router = APIRouter(prefix="/api/vault")


class VaultTreeResponse(BaseModel):
    nodes: list[VaultNode]


class VaultNoteResponse(BaseModel):
    path: str
    content: str


@router.get("/tree", response_model=VaultTreeResponse)
def get_vault_tree() -> VaultTreeResponse:
    return VaultTreeResponse(nodes=list_vault_tree(load_manifest()))


@router.get("/note", response_model=VaultNoteResponse)
def get_vault_note(path: str) -> VaultNoteResponse:
    return VaultNoteResponse(
        path=path,
        content=read_vault_note(load_manifest(), path),
    )
