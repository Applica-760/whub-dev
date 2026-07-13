"""Knowledge operations shared by CLI and web adapters."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from whub.core.target import TargetItem, on_targets
from whub.models import (
    Knowledge,
    KnowledgeDefinition,
    KnowledgeError,
    KnowledgeException,
    KnowledgePolicy,
    KnowledgeRelation,
    Manifest,
    RemoteResource,
    SymlinkResource,
    load_knowledge,
    workspace_hub_resource,
)
from whub.services.errors import ServiceError


KNOWLEDGE_RELATIVE_PATH = Path("docs/knowledge.yaml")


@dataclass(frozen=True)
class KnowledgeQueryResult:
    definitions: list[KnowledgeDefinition]
    relations: list[KnowledgeRelation]
    policies: list[KnowledgePolicy]
    exceptions: list[KnowledgeException]

    def is_empty(self) -> bool:
        return not any(
            (self.definitions, self.relations, self.policies, self.exceptions)
        )


def _resolve_resource(
    manifest: Manifest,
    project: str,
) -> SymlinkResource | RemoteResource:
    resolved_project = manifest.resolve_project(project)
    if resolved_project is None:
        raise ServiceError(f"unknown project: {project}")
    if resolved_project.resource is None:
        if resolved_project.name == "workspace-hub":
            return workspace_hub_resource()
        raise ServiceError(f"project has no resource: {project}")
    return resolved_project.resource


def _load_path(path: Path) -> Knowledge:
    try:
        return load_knowledge(path)
    except KnowledgeError as error:
        raise ServiceError(str(error)) from error


def _load_local(
    resource: SymlinkResource,
    data: None,
) -> Knowledge:
    del data
    return _load_path(Path(resource.source) / KNOWLEDGE_RELATIVE_PATH)


def _load_remote(
    resource: RemoteResource,
    data: None,
) -> Knowledge:
    del data
    root = resource._resolved_workspace_path
    if not root.is_dir():
        raise ServiceError(f"remote workspace path is not available: {root}")
    return _load_path(root / KNOWLEDGE_RELATIVE_PATH)


def load_project_knowledge(manifest: Manifest, project: str) -> Knowledge:
    """Load a project's fixed-path Knowledge YAML."""
    target = TargetItem(_resolve_resource(manifest, project), None)
    return on_targets([target], local=_load_local, remote=_load_remote)[0]


def _matches(term: str, *values: str | None) -> bool:
    return any(term in value.casefold() for value in values if value is not None)


def query_knowledge(knowledge: Knowledge, term: str) -> KnowledgeQueryResult:
    """Find direct text matches and entries connected by direct references."""
    normalized = term.strip().casefold()
    if not normalized:
        raise ServiceError("knowledge query term is required")

    definitions_by_id = {
        definition.id: definition for definition in knowledge.definitions
    }
    policies_by_id = {policy.id: policy for policy in knowledge.policies}

    definitions = [
        definition
        for definition in knowledge.definitions
        if _matches(
            normalized,
            definition.id,
            definition.name,
            definition.definition,
        )
    ]

    relations = []
    for relation in knowledge.relations:
        subject = definitions_by_id.get(relation.subject)
        object_ = definitions_by_id.get(relation.object)
        if _matches(
            normalized,
            relation.id,
            relation.subject,
            subject.name if subject is not None else None,
            subject.definition if subject is not None else None,
            relation.predicate,
            relation.object,
            object_.name if object_ is not None else None,
            object_.definition if object_ is not None else None,
            relation.cardinality,
        ):
            relations.append(relation)

    related_definition_ids = {
        entry_id
        for relation in relations
        for entry_id in (relation.subject, relation.object)
    }
    matched_definition_ids = {
        definition.id for definition in definitions
    } | related_definition_ids
    definitions = [
        definition
        for definition in knowledge.definitions
        if definition.id in matched_definition_ids
    ]

    policies = [
        policy
        for policy in knowledge.policies
        if _matches(normalized, policy.id, policy.statement)
    ]

    exceptions = []
    for exception in knowledge.exceptions:
        policy = policies_by_id.get(exception.exception_to)
        if _matches(
            normalized,
            exception.id,
            exception.exception_to,
            policy.statement if policy is not None else None,
            exception.condition,
            exception.statement,
        ):
            exceptions.append(exception)

    matched_policy_ids = {policy.id for policy in policies} | {
        exception.exception_to for exception in exceptions
    }
    policies = [
        policy for policy in knowledge.policies if policy.id in matched_policy_ids
    ]

    return KnowledgeQueryResult(definitions, relations, policies, exceptions)
