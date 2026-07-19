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
    load_project_knowledge,
    query_knowledge,
)
from whub.services.knowledge_operation import (
    add_constraint,
    add_definition,
    add_exception,
    add_policy,
    add_relation,
    add_relation_type,
    init_project_knowledge,
    remove_knowledge,
)


DEFAULT_PROJECT = "workspace-hub"
CATEGORIES = {
    "def": "definitions",
    "relation-type": "relation_types",
    "rel": "relations",
    "pol": "policies",
    "con": "constraints",
    "exc": "exceptions",
}
ID_PREFIXES = {
    "def": "DEF",
    "rel": "REL",
    "pol": "POL",
    "con": "CON",
    "exc": "EXC",
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


def _dump_groups(groups: tuple[tuple[str, list[object]], ...]) -> str:
    data = {
        name: [entry.model_dump(exclude_none=True) for entry in entries]
        for name, entries in groups
    }
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False).rstrip()


def _result_groups(result: KnowledgeQueryResult) -> tuple[tuple[str, list[object]], ...]:
    return tuple(
        (name, entries)
        for name, entries in (
            ("definitions", result.definitions),
            ("relation_types", result.relation_types),
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
    loaded = _load(ctx, project)
    click.echo(
        f"valid {project}: "
        f"{len(loaded.definitions)} definitions, "
        f"{len(loaded.relation_types)} relation types, "
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
    """Query a project's knowledge by ID or text."""
    loaded = _load(ctx, project)
    result = _invoke(lambda: query_knowledge(loaded, term))
    if result.is_empty():
        raise click.ClickException(f"no knowledge matches: {term}")
    click.echo(_dump_groups(_result_groups(result)))


@knowledge.command("init")
@_project_option
@click.pass_context
def initialize(ctx: click.Context, project: str) -> None:
    """Create an empty schema v3 Knowledge YAML."""
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
@click.argument("name")
@click.argument("definition")
@click.option("--ref")
@_project_option
@click.pass_context
def add_def(
    ctx: click.Context,
    name: str,
    definition: str,
    ref: str | None,
    project: str,
) -> None:
    """Add a Definition."""
    entry = _invoke(
        lambda: add_definition(get_manifest(ctx), project, name, definition, ref)
    )
    click.echo(f"added {entry.id}")


@add.command("relation-type")
@click.argument("name")
@click.argument("definition")
@_project_option
@click.pass_context
def add_relation_type_command(
    ctx: click.Context,
    name: str,
    definition: str,
    project: str,
) -> None:
    """Add a Relation type."""
    entry = _invoke(
        lambda: add_relation_type(get_manifest(ctx), project, name, definition)
    )
    click.echo(f"added relation type {entry.name}")


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
    entry = _invoke(
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
    click.echo(f"added {entry.id}")


@add.command("pol")
@click.argument("statement")
@click.option("--ref")
@_project_option
@click.pass_context
def add_pol(
    ctx: click.Context,
    statement: str,
    ref: str | None,
    project: str,
) -> None:
    """Add a Policy."""
    entry = _invoke(lambda: add_policy(get_manifest(ctx), project, statement, ref))
    click.echo(f"added {entry.id}")


@add.command("con")
@click.argument("statement")
@click.option("--ref")
@_project_option
@click.pass_context
def add_con(
    ctx: click.Context,
    statement: str,
    ref: str | None,
    project: str,
) -> None:
    """Add a Constraint."""
    entry = _invoke(
        lambda: add_constraint(get_manifest(ctx), project, statement, ref)
    )
    click.echo(f"added {entry.id}")


@add.command("exc")
@click.argument("exception_to")
@click.argument("condition")
@click.argument("statement")
@click.option("--ref")
@_project_option
@click.pass_context
def add_exc(
    ctx: click.Context,
    exception_to: str,
    condition: str,
    statement: str,
    ref: str | None,
    project: str,
) -> None:
    """Add an Exception."""
    entry = _invoke(
        lambda: add_exception(
            get_manifest(ctx),
            project,
            exception_to,
            condition,
            statement,
            ref,
        )
    )
    click.echo(f"added {entry.id}")


@knowledge.command("rm")
@click.argument("category", type=click.Choice(tuple(CATEGORIES)))
@click.argument("target")
@_project_option
@click.pass_context
def remove(
    ctx: click.Context,
    category: str,
    target: str,
    project: str,
) -> None:
    """Remove one Knowledge entry by category and number or name."""
    if category == "relation-type":
        normalized = target
    else:
        try:
            number = int(target)
        except ValueError as error:
            raise click.BadParameter(
                "expected a positive integer",
                param_hint="target",
            ) from error
        if number < 1:
            raise click.BadParameter(
                "expected a positive integer",
                param_hint="target",
            )
        normalized = f"{ID_PREFIXES[category]}-{number:03d}"
    _invoke(lambda: remove_knowledge(get_manifest(ctx), project, normalized))
    click.echo(f"removed {normalized}")
