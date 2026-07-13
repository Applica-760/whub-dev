"""whub knowledge — validate and query project Knowledge YAML."""
from __future__ import annotations

import click
import yaml

from whub.commands import get_manifest
from whub.models import Knowledge, project_names
from whub.services.errors import ServiceError
from whub.services.knowledge import (
    KnowledgeQueryResult,
    load_project_knowledge,
    query_knowledge,
)


@click.group()
def knowledge() -> None:
    """Validate and query project knowledge."""


def _load(ctx: click.Context, project: str) -> Knowledge:
    try:
        return load_project_knowledge(get_manifest(ctx), project)
    except ServiceError as error:
        raise click.ClickException(str(error)) from error


@knowledge.command()
@click.argument("project", shell_complete=project_names)
@click.pass_context
def check(ctx: click.Context, project: str) -> None:
    """Validate a project's docs/knowledge.yaml."""
    loaded = _load(ctx, project)
    click.echo(
        f"valid {project}: "
        f"{len(loaded.definitions)} definitions, "
        f"{len(loaded.relations)} relations, "
        f"{len(loaded.policies)} policies, "
        f"{len(loaded.exceptions)} exceptions"
    )


def _dump_result(result: KnowledgeQueryResult) -> str:
    groups = (
        ("definitions", result.definitions),
        ("relations", result.relations),
        ("policies", result.policies),
        ("exceptions", result.exceptions),
    )
    data = {
        name: [entry.model_dump(exclude_none=True) for entry in entries]
        for name, entries in groups
        if entries
    }
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False).rstrip()


@knowledge.command()
@click.argument("term")
@click.argument("project", shell_complete=project_names)
@click.pass_context
def query(ctx: click.Context, term: str, project: str) -> None:
    """Query a project's knowledge by ID or text."""
    loaded = _load(ctx, project)
    try:
        result = query_knowledge(loaded, term)
    except ServiceError as error:
        raise click.ClickException(str(error)) from error
    if result.is_empty():
        raise click.ClickException(f"no knowledge matches: {term}")
    click.echo(_dump_result(result))
