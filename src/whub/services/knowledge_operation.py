"""Operations that mutate a project's Knowledge YAML."""
from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from pydantic import ValidationError

from whub.models import (
    Knowledge,
    KnowledgeConstraint,
    KnowledgeDefinition,
    KnowledgeException,
    KnowledgePolicy,
    KnowledgeRelation,
    KnowledgeRelationType,
    Manifest,
)
from whub.services.errors import NotFoundError, ServiceError
from whub.services.knowledge import (
    load_project_knowledge,
    resolve_project_knowledge_path,
    save_project_knowledge,
)


T = TypeVar("T")


def init_project_knowledge(manifest: Manifest, project: str) -> Knowledge:
    """Create an empty schema v3 Knowledge YAML without overwriting one."""
    path = resolve_project_knowledge_path(manifest, project)
    if path.exists():
        raise ServiceError(f"knowledge file already exists: {path}")
    knowledge = Knowledge(
        schema_version=3,
        definitions=[],
        relation_types=[],
        relations=[],
        policies=[],
        constraints=[],
        exceptions=[],
    )
    save_project_knowledge(path, knowledge)
    return knowledge


def _operate(
    manifest: Manifest,
    project: str,
    operation: Callable[[Knowledge], T],
) -> T:
    path = resolve_project_knowledge_path(manifest, project)
    knowledge = load_project_knowledge(manifest, project)
    try:
        result = operation(knowledge)
    except ValidationError as error:
        raise ServiceError(f"invalid Knowledge input: {error}") from error
    save_project_knowledge(path, knowledge)
    return result


def _next_id(entries: list[object], prefix: str) -> str:
    numbers = [
        int(entry.id.removeprefix(f"{prefix}-"))
        for entry in entries
        if hasattr(entry, "id")
    ]
    return f"{prefix}-{max(numbers, default=0) + 1:03d}"


def add_definition(
    manifest: Manifest,
    project: str,
    name: str,
    definition: str,
    ref: str | None = None,
) -> KnowledgeDefinition:
    def operation(knowledge: Knowledge) -> KnowledgeDefinition:
        entry = KnowledgeDefinition(
            id=_next_id(knowledge.definitions, "DEF"),
            name=name,
            definition=definition,
            ref=ref,
        )
        knowledge.definitions.append(entry)
        return entry

    return _operate(manifest, project, operation)


def add_relation_type(
    manifest: Manifest,
    project: str,
    name: str,
    definition: str,
) -> KnowledgeRelationType:
    def operation(knowledge: Knowledge) -> KnowledgeRelationType:
        entry = KnowledgeRelationType(name=name, definition=definition)
        knowledge.relation_types.append(entry)
        return entry

    return _operate(manifest, project, operation)


def add_relation(
    manifest: Manifest,
    project: str,
    subject: str,
    predicate: str,
    object_: str,
    cardinality: str | None = None,
    ref: str | None = None,
) -> KnowledgeRelation:
    def operation(knowledge: Knowledge) -> KnowledgeRelation:
        entry = KnowledgeRelation(
            id=_next_id(knowledge.relations, "REL"),
            subject=subject,
            predicate=predicate,
            object=object_,
            cardinality=cardinality,
            ref=ref,
        )
        knowledge.relations.append(entry)
        return entry

    return _operate(manifest, project, operation)


def add_policy(
    manifest: Manifest,
    project: str,
    statement: str,
    ref: str | None = None,
) -> KnowledgePolicy:
    def operation(knowledge: Knowledge) -> KnowledgePolicy:
        entry = KnowledgePolicy(
            id=_next_id(knowledge.policies, "POL"),
            statement=statement,
            ref=ref,
        )
        knowledge.policies.append(entry)
        return entry

    return _operate(manifest, project, operation)


def add_constraint(
    manifest: Manifest,
    project: str,
    statement: str,
    ref: str | None = None,
) -> KnowledgeConstraint:
    def operation(knowledge: Knowledge) -> KnowledgeConstraint:
        entry = KnowledgeConstraint(
            id=_next_id(knowledge.constraints, "CON"),
            statement=statement,
            ref=ref,
        )
        knowledge.constraints.append(entry)
        return entry

    return _operate(manifest, project, operation)


def add_exception(
    manifest: Manifest,
    project: str,
    exception_to: str,
    condition: str,
    statement: str,
    ref: str | None = None,
) -> KnowledgeException:
    def operation(knowledge: Knowledge) -> KnowledgeException:
        entry = KnowledgeException(
            id=_next_id(knowledge.exceptions, "EXC"),
            exception_to=exception_to,
            condition=condition,
            statement=statement,
            ref=ref,
        )
        knowledge.exceptions.append(entry)
        return entry

    return _operate(manifest, project, operation)


def remove_knowledge(manifest: Manifest, project: str, target: str) -> None:
    """Remove one ID or relation type name unless another entry references it."""
    def operation(knowledge: Knowledge) -> None:
        if any(item.name == target for item in knowledge.relation_types):
            references = [
                relation.id
                for relation in knowledge.relations
                if relation.predicate == target
            ]
            if references:
                raise ServiceError(
                    f"knowledge target is referenced by: {', '.join(references)}"
                )
            knowledge.relation_types = [
                item for item in knowledge.relation_types if item.name != target
            ]
            return

        references = [
            relation.id
            for relation in knowledge.relations
            if target in (relation.subject, relation.object)
        ]
        references.extend(
            exception.id
            for exception in knowledge.exceptions
            if exception.exception_to == target
        )
        if references:
            raise ServiceError(
                f"knowledge target is referenced by: {', '.join(references)}"
            )

        groups = (
            knowledge.definitions,
            knowledge.relations,
            knowledge.policies,
            knowledge.constraints,
            knowledge.exceptions,
        )
        for entries in groups:
            for index, entry in enumerate(entries):
                if entry.id == target:
                    entries.pop(index)
                    return
        raise NotFoundError(f"knowledge target not found: {target}")

    _operate(manifest, project, operation)
