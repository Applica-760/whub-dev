"""whub knowledge — validate, query, and update project Knowledge YAML."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import click
import yaml

from whub.commands import get_manifest
from whub.models import Knowledge, project_names
from whub.services.errors import ServiceError
from whub.services.knowledge import (
    KnowledgeQueryResult,
    check_project_knowledge,
    load_project_knowledge,
    query_knowledge,
)
from whub.services.knowledge_operation import (
    add_constraint,
    add_definition,
    add_exception,
    add_policy,
    add_relation,
    init_project_knowledge,
    remove_knowledge,
    remove_relation,
)


DEFAULT_PROJECT = "workspace-hub"
CATEGORIES = {
    "def": "definitions",
    "rel": "relations",
    "pol": "policies",
    "con": "constraints",
    "exc": "exceptions",
}


def _project_option(function: Callable[..., Any]) -> Callable[..., Any]:
    return click.option(
        "--project",
        default=DEFAULT_PROJECT,
        show_default=True,
        shell_complete=project_names,
        help="Target project.",
    )(function)


@click.group()
def knowledge() -> None:
    """Validate, query, and update project knowledge."""


def _load(ctx: click.Context, project: str) -> Knowledge:
    try:
        return load_project_knowledge(get_manifest(ctx), project)
    except ServiceError as error:
        raise click.ClickException(str(error)) from error


def _dump_groups(
    groups: tuple[tuple[str, dict[str, object] | list[object]], ...],
) -> str:
    data = {}
    for name, entries in groups:
        if isinstance(entries, dict):
            data[name] = {
                slug: entry.model_dump(exclude_none=True)
                for slug, entry in entries.items()
            }
        else:
            data[name] = [entry.model_dump(exclude_none=True) for entry in entries]
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False).rstrip()


def _result_groups(
    result: KnowledgeQueryResult,
) -> tuple[tuple[str, dict[str, object] | list[object]], ...]:
    return tuple(
        (name, entries)
        for name, entries in (
            ("definitions", result.definitions),
            ("relations", result.relations),
            ("policies", result.policies),
            ("constraints", result.constraints),
            ("exceptions", result.exceptions),
        )
        if entries
    )


def _invoke(operation: Callable[[], Any]) -> Any:
    try:
        return operation()
    except ServiceError as error:
        raise click.ClickException(str(error)) from error


@knowledge.command()
@_project_option
@click.pass_context
def check(ctx: click.Context, project: str) -> None:
    """Validate a project's docs/knowledge.yaml."""
    loaded = _invoke(lambda: check_project_knowledge(get_manifest(ctx), project))
    click.echo(
        f"valid {project}: "
        f"{len(loaded.definitions)} definitions, "
        f"{len(loaded.relations)} relations, "
        f"{len(loaded.policies)} policies, "
        f"{len(loaded.constraints)} constraints, "
        f"{len(loaded.exceptions)} exceptions"
    )


@knowledge.command()
@click.argument("term")
@_project_option
@click.pass_context
def query(ctx: click.Context, term: str, project: str) -> None:
    """Query a project's knowledge by slug, reference, or text."""
    loaded = _load(ctx, project)
    result = _invoke(lambda: query_knowledge(loaded, term))
    if result.is_empty():
        raise click.ClickException(f"no knowledge matches: {term}")
    click.echo(_dump_groups(_result_groups(result)))


@knowledge.command("init")
@_project_option
@click.pass_context
def initialize(ctx: click.Context, project: str) -> None:
    """Create an empty schema v4 Knowledge YAML."""
    _invoke(lambda: init_project_knowledge(get_manifest(ctx), project))
    click.echo(f"initialized {project}")


@knowledge.command("ls")
@click.argument("category", type=click.Choice(tuple(CATEGORIES)))
@_project_option
@click.pass_context
def list_category(ctx: click.Context, category: str, project: str) -> None:
    """List one Knowledge category."""
    loaded = _load(ctx, project)
    field = CATEGORIES[category]
    click.echo(_dump_groups(((field, getattr(loaded, field)),)))


@knowledge.group()
def add() -> None:
    """Add one Knowledge entry."""


@add.command("def")
@click.argument("slug")
@click.argument("name")
@click.argument("definition")
@click.option("--ref")
@_project_option
@click.pass_context
def add_def(
    ctx: click.Context,
    slug: str,
    name: str,
    definition: str,
    ref: str | None,
    project: str,
) -> None:
    """Add a Definition."""
    _invoke(
        lambda: add_definition(get_manifest(ctx), project, slug, name, definition, ref)
    )
    click.echo(f"added def:{slug}")


@add.command("rel")
@click.argument("subject")
@click.argument("predicate")
@click.argument("object_id")
@click.option("--cardinality")
@click.option("--ref")
@_project_option
@click.pass_context
def add_rel(
    ctx: click.Context,
    subject: str,
    predicate: str,
    object_id: str,
    cardinality: str | None,
    ref: str | None,
    project: str,
) -> None:
    """Add a Relation."""
    _invoke(
        lambda: add_relation(
            get_manifest(ctx),
            project,
            subject,
            predicate,
            object_id,
            cardinality,
            ref,
        )
    )
    click.echo(f"added {subject} {predicate} {object_id}")


@add.command("pol")
@click.argument("slug")
@click.argument("statement")
@click.option("--ref")
@_project_option
@click.pass_context
def add_pol(
    ctx: click.Context,
    slug: str,
    statement: str,
    ref: str | None,
    project: str,
) -> None:
    """Add a Policy."""
    _invoke(lambda: add_policy(get_manifest(ctx), project, slug, statement, ref))
    click.echo(f"added pol:{slug}")


@add.command("con")
@click.argument("slug")
@click.argument("statement")
@click.option("--ref")
@_project_option
@click.pass_context
def add_con(
    ctx: click.Context,
    slug: str,
    statement: str,
    ref: str | None,
    project: str,
) -> None:
    """Add a Constraint."""
    _invoke(lambda: add_constraint(get_manifest(ctx), project, slug, statement, ref))
    click.echo(f"added con:{slug}")


@add.command("exc")
@click.argument("slug")
@click.argument("exception_to")
@click.argument("condition")
@click.argument("statement")
@click.option("--ref")
@_project_option
@click.pass_context
def add_exc(
    ctx: click.Context,
    slug: str,
    exception_to: str,
    condition: str,
    statement: str,
    ref: str | None,
    project: str,
) -> None:
    """Add an Exception."""
    _invoke(
        lambda: add_exception(
            get_manifest(ctx),
            project,
            slug,
            exception_to,
            condition,
            statement,
            ref,
        )
    )
    click.echo(f"added exc:{slug}")


@knowledge.command("rm")
@click.argument("category", type=click.Choice(tuple(CATEGORIES)))
@click.argument("targets", nargs=-1, required=True)
@_project_option
@click.pass_context
def remove(
    ctx: click.Context,
    category: str,
    targets: tuple[str, ...],
    project: str,
) -> None:
    """Remove one Knowledge entry by slug or Relation composite key."""
    manifest = get_manifest(ctx)
    if category == "rel":
        if len(targets) != 3:
            raise click.UsageError("rm rel requires SUBJECT PREDICATE OBJECT")
        subject, predicate, object_id = targets
        _invoke(
            lambda: remove_relation(
                manifest,
                project,
                subject,
                predicate,
                object_id,
            )
        )
        click.echo(f"removed {subject} {predicate} {object_id}")
        return

    if len(targets) != 1:
        raise click.UsageError(f"rm {category} requires SLUG")
    target = f"{category}:{targets[0]}"
    _invoke(lambda: remove_knowledge(manifest, project, target))
    click.echo(f"removed {target}")
