"""Daily JSON API."""

from __future__ import annotations

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from whub.models import load_manifest
from whub.services.daily import append_daily_entry


router = APIRouter(prefix="/api/daily")


class CreateDailyEntryRequest(BaseModel):
    body: str
    energy: int | None = Field(default=None, ge=1, le=5)


class DailyEntryResponse(BaseModel):
    path: str


@router.post("", response_model=DailyEntryResponse, status_code=status.HTTP_201_CREATED)
def create_daily_entry(request: CreateDailyEntryRequest) -> DailyEntryResponse:
    path = append_daily_entry(load_manifest(), request.body, request.energy)
    return DailyEntryResponse(path=str(path.relative_to(path.parents[1])))
