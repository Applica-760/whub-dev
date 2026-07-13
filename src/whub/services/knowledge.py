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


def _load_local(
    resource: SymlinkResource,
    data: None,
) -> Knowledge:
    del data
    return load_knowledge(Path(resource.source) / KNOWLEDGE_RELATIVE_PATH)


def _load_remote(
    resource: RemoteResource,
    data: None,
) -> Knowledge:
    del data
    root = resource._resolved_workspace_path
    if not root.is_dir():
        raise ServiceError(f"remote workspace path is not available: {root}")
    return load_knowledge(root / KNOWLEDGE_RELATIVE_PATH)


def load_project_knowledge(manifest: Manifest, project: str) -> Knowledge:
    """Load a project's fixed-path Knowledge YAML."""
    target = TargetItem(_resolve_resource(manifest, project), None)
    try:
        return on_targets([target], local=_load_local, remote=_load_remote)[0]
    except KnowledgeError as error:
        raise ServiceError(str(error)) from error


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
    ]

    policies = [
        policy
        for policy in knowledge.policies
        if _matches(normalized, policy.id, policy.ref, policy.statement)
    ]

    matched_policy_ids = {policy.id for policy in policies}
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
        or exception.exception_to in matched_policy_ids
    ]

    return KnowledgeQueryResult(definitions, relations, policies, exceptions)
