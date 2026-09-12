"""Read-only GitHub Issue list API."""

from __future__ import annotations

import json

from fastapi import APIRouter
from pydantic import BaseModel

from whub.core.context import current_context
from whub.core.github import github_repository, run_gh
from whub.services.errors import ServiceError
from whub.services.manifest import load_manifest


router = APIRouter(prefix="/api/issues")


class IssueResponse(BaseModel):
    number: int
    title: str
    url: str


@router.get("/{project}", response_model=list[IssueResponse])
def list_issues(project: str) -> list[IssueResponse]:
    manifest = load_manifest()
    resolved = manifest.resolve_project(project)
    if resolved is None or resolved.resource is None or resolved.resource.git is None:
        raise ServiceError(f"project has no git repository: {project}")
    try:
        repository = github_repository(resolved.resource.git.url)
    except ValueError as error:
        raise ServiceError(str(error)) from error
    result = run_gh(
        None,
        current_context().workspace_root,
        "issue",
        "list",
        "--repo",
        repository,
        "--state",
        "open",
        "--json",
        "number,title,url",
    )
    if result.returncode != 0:
        raise ServiceError(result.stderr.strip() or "failed to list GitHub Issues")
    try:
        issues = json.loads(result.stdout)
        return [IssueResponse.model_validate(issue) for issue in issues]
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise ServiceError("gh issue list returned invalid data") from error
