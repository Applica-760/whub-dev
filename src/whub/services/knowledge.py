"""Knowledge operations shared by CLI and web adapters."""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

import yaml
from pydantic import ValidationError

from whub.core.target import TargetItem, on_targets
from whub.models import (
    Knowledge,
    KnowledgeConstraint,
    KnowledgeDefinition,
    KnowledgeError,
    KnowledgeException,
    KnowledgePolicy,
    KnowledgeRelation,
    KnowledgeRelationType,
    Manifest,
    RemoteResource,
    SymlinkResource,
    load_knowledge,
)
from whub.services.errors import NotFoundError, ServiceError
from whub.services.project_content import resolve_project_content_resource


KNOWLEDGE_RELATIVE_PATH = Path("docs/knowledge.yaml")


@dataclass(frozen=True)
class KnowledgeQueryResult:
    definitions: list[KnowledgeDefinition]
    relation_types: list[KnowledgeRelationType]
    relations: list[KnowledgeRelation]
    policies: list[KnowledgePolicy]
    constraints: list[KnowledgeConstraint]
    exceptions: list[KnowledgeException]

    def is_empty(self) -> bool:
        return not any(
            (
                self.definitions,
                self.relation_types,
                self.relations,
                self.policies,
                self.constraints,
                self.exceptions,
            )
        )


def resolve_project_knowledge_path(manifest: Manifest, project: str) -> Path:
    target = TargetItem(resolve_project_content_resource(manifest, project), None)

    def local(resource: SymlinkResource, data: None) -> Path:
        del data
        return Path(resource.source) / KNOWLEDGE_RELATIVE_PATH

    def remote(resource: RemoteResource, data: None) -> Path:
        del data
        root = resource._resolved_workspace_path
        if not root.is_dir():
            raise ServiceError(f"remote workspace path is not available: {root}")
        return root / KNOWLEDGE_RELATIVE_PATH

    return on_targets([target], local=local, remote=remote)[0]


def _load_path(path: Path) -> Knowledge:
    if not path.is_file():
        raise NotFoundError(f"knowledge file not found: {path}")
    return load_knowledge(path)


def load_project_knowledge(manifest: Manifest, project: str) -> Knowledge:
    """Load a project's fixed-path Knowledge YAML."""
    try:
        return _load_path(resolve_project_knowledge_path(manifest, project))
    except KnowledgeError as error:
        raise ServiceError(str(error)) from error


def _validate_knowledge(knowledge: Knowledge) -> Knowledge:
    try:
        return Knowledge.model_validate(knowledge.model_dump())
    except ValidationError as error:
        raise ServiceError(f"invalid Knowledge update: {error}") from error


def save_project_knowledge(path: Path, knowledge: Knowledge) -> None:
    validated = _validate_knowledge(knowledge)
    content = yaml.safe_dump(
        validated.model_dump(exclude_none=True),
        allow_unicode=True,
        sort_keys=False,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        if path.exists():
            temporary_path.chmod(path.stat().st_mode)
        os.replace(temporary_path, path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def _matches(term: str, *values: str | None) -> bool:
    return any(term in value.casefold() for value in values if value is not None)


def query_knowledge(knowledge: Knowledge, term: str) -> KnowledgeQueryResult:
    """Find direct text matches and entries connected by direct references."""
    normalized = term.strip().casefold()
    if not normalized:
        raise ServiceError("knowledge query term is required")

    definitions = [
        definition
        for definition in knowledge.definitions
        if _matches(
            normalized,
            definition.id,
            definition.ref,
            definition.name,
            definition.definition,
        )
    ]

    matched_definition_ids = {definition.id for definition in definitions}
    relation_types = [
        relation_type
        for relation_type in knowledge.relation_types
        if _matches(normalized, relation_type.name, relation_type.definition)
    ]
    matched_relation_type_names = {item.name for item in relation_types}
    relations = [
        relation
        for relation in knowledge.relations
        if _matches(
            normalized,
            relation.id,
            relation.ref,
            relation.subject,
            relation.predicate,
            relation.object,
            relation.cardinality,
        )
        or relation.subject in matched_definition_ids
        or relation.object in matched_definition_ids
        or relation.predicate in matched_relation_type_names
    ]
    matched_relation_predicates = {relation.predicate for relation in relations}
    relation_types = [
        relation_type
        for relation_type in knowledge.relation_types
        if relation_type.name in matched_relation_type_names
        or relation_type.name in matched_relation_predicates
    ]

    policies = [
        policy
        for policy in knowledge.policies
        if _matches(normalized, policy.id, policy.ref, policy.statement)
    ]

    constraints = [
        constraint
        for constraint in knowledge.constraints
        if _matches(normalized, constraint.id, constraint.ref, constraint.statement)
    ]

    matched_exception_target_ids = {
        *(policy.id for policy in policies),
        *(constraint.id for constraint in constraints),
    }
    exceptions = [
        exception
        for exception in knowledge.exceptions
        if _matches(
            normalized,
            exception.id,
            exception.ref,
            exception.exception_to,
            exception.condition,
            exception.statement,
        )
        or exception.exception_to in matched_exception_target_ids
    ]

    return KnowledgeQueryResult(
        definitions,
        relation_types,
        relations,
        policies,
        constraints,
        exceptions,
    )
