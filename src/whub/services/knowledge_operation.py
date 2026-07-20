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
    """Create an empty schema v4 Knowledge YAML without overwriting one."""
    path = resolve_project_knowledge_path(manifest, project)
    if path.exists():
        raise ServiceError(f"knowledge file already exists: {path}")
    knowledge = Knowledge(
        schema_version=4,
        definitions={},
        relations=[],
        policies={},
        constraints={},
        exceptions={},
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


def add_definition(
    manifest: Manifest,
    project: str,
    slug: str,
    name: str,
    definition: str,
    ref: str | None = None,
) -> KnowledgeDefinition:
    def operation(knowledge: Knowledge) -> KnowledgeDefinition:
        if slug in knowledge.definitions:
            raise ServiceError(f"knowledge slug already exists: def:{slug}")
        entry = KnowledgeDefinition(
            name=name,
            definition=definition,
            ref=ref,
        )
        knowledge.definitions[slug] = entry
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
        key = (subject, predicate, object_)
        if any(
            (item.subject, item.predicate, item.object) == key
            for item in knowledge.relations
        ):
            raise ServiceError(
                "knowledge relation already exists: "
                f"{subject} {predicate} {object_}"
            )
        entry = KnowledgeRelation(
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
    slug: str,
    statement: str,
    ref: str | None = None,
) -> KnowledgePolicy:
    def operation(knowledge: Knowledge) -> KnowledgePolicy:
        if slug in knowledge.policies:
            raise ServiceError(f"knowledge slug already exists: pol:{slug}")
        entry = KnowledgePolicy(statement=statement, ref=ref)
        knowledge.policies[slug] = entry
        return entry

    return _operate(manifest, project, operation)


def add_constraint(
    manifest: Manifest,
    project: str,
    slug: str,
    statement: str,
    ref: str | None = None,
) -> KnowledgeConstraint:
    def operation(knowledge: Knowledge) -> KnowledgeConstraint:
        if slug in knowledge.constraints:
            raise ServiceError(f"knowledge slug already exists: con:{slug}")
        entry = KnowledgeConstraint(statement=statement, ref=ref)
        knowledge.constraints[slug] = entry
        return entry

    return _operate(manifest, project, operation)


def add_exception(
    manifest: Manifest,
    project: str,
    slug: str,
    exception_to: str,
    condition: str,
    statement: str,
    ref: str | None = None,
) -> KnowledgeException:
    def operation(knowledge: Knowledge) -> KnowledgeException:
        if slug in knowledge.exceptions:
            raise ServiceError(f"knowledge slug already exists: exc:{slug}")
        entry = KnowledgeException(
            exception_to=exception_to,
            condition=condition,
            statement=statement,
            ref=ref,
        )
        knowledge.exceptions[slug] = entry
        return entry

    return _operate(manifest, project, operation)


def remove_knowledge(manifest: Manifest, project: str, target: str) -> None:
    """Remove one category-qualified entry unless another entry references it."""
    def operation(knowledge: Knowledge) -> None:
        references = [
            f"{relation.subject} {relation.predicate} {relation.object}"
            for relation in knowledge.relations
            if target in (relation.subject, relation.object)
        ]
        references.extend(
            f"exc:{slug}"
            for slug, exception in knowledge.exceptions.items()
            if exception.exception_to == target
        )
        if references:
            raise ServiceError(
                f"knowledge target is referenced by: {', '.join(references)}"
            )

        prefix, separator, slug = target.partition(":")
        groups = {
            "def": knowledge.definitions,
            "pol": knowledge.policies,
            "con": knowledge.constraints,
            "exc": knowledge.exceptions,
        }
        entries = groups.get(prefix) if separator else None
        if entries is None or slug not in entries:
            raise NotFoundError(f"knowledge target not found: {target}")
        entries.pop(slug)

    _operate(manifest, project, operation)


def remove_relation(
    manifest: Manifest,
    project: str,
    subject: str,
    predicate: str,
    object_: str,
) -> None:
    """Remove one Relation identified by its composite key."""
    def operation(knowledge: Knowledge) -> None:
        for index, relation in enumerate(knowledge.relations):
            if (
                relation.subject,
                relation.predicate,
                relation.object,
            ) == (subject, predicate, object_):
                knowledge.relations.pop(index)
                return
        raise NotFoundError(
            "knowledge relation not found: "
            f"{subject} {predicate} {object_}"
        )

    _operate(manifest, project, operation)
