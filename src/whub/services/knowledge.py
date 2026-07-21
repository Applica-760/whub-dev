"""Knowledge operations shared by CLI and web adapters."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

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
    definitions: dict[str, KnowledgeDefinition]
    relations: list[KnowledgeRelation]
    policies: dict[str, KnowledgePolicy]
    constraints: dict[str, KnowledgeConstraint]
    exceptions: dict[str, KnowledgeException]

    def is_empty(self) -> bool:
        return not any(
            (
                self.definitions,
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


def _knowledge_refs(knowledge: Knowledge) -> Iterator[tuple[str, str]]:
    groups = (
        ("def", knowledge.definitions),
        ("pol", knowledge.policies),
        ("con", knowledge.constraints),
        ("exc", knowledge.exceptions),
    )
    for prefix, entries in groups:
        for slug, entry in entries.items():
            if entry.ref is not None:
                yield f"{prefix}:{slug}", entry.ref

    for relation in knowledge.relations:
        if relation.ref is not None:
            yield (
                f"rel:{relation.subject} {relation.predicate} {relation.object}",
                relation.ref,
            )


def check_project_knowledge(manifest: Manifest, project: str) -> Knowledge:
    """Load Knowledge and validate project-relative ref paths."""
    knowledge_path = resolve_project_knowledge_path(manifest, project)
    knowledge = load_project_knowledge(manifest, project)
    project_root = knowledge_path.parent.parent
    missing: list[str] = []

    for reference, ref in _knowledge_refs(knowledge):
        parsed = urlsplit(ref)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        relative_path = Path(parsed.path)
        if relative_path.is_absolute():
            continue
        if ".." in relative_path.parts:
            raise ServiceError(
                f"knowledge ref escapes project root: {reference}: {ref}"
            )
        if not (project_root / relative_path).exists():
            missing.append(f"{reference}: {ref}")

    if missing:
        raise ServiceError(f"missing knowledge refs: {', '.join(missing)}")
    return knowledge


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

    definitions = {
        slug: definition
        for slug, definition in knowledge.definitions.items()
        if _matches(
            normalized,
            slug,
            f"def:{slug}",
            definition.ref,
            definition.name,
            definition.definition,
        )
    }

    policies = {
        slug: policy
        for slug, policy in knowledge.policies.items()
        if _matches(normalized, slug, f"pol:{slug}", policy.ref, policy.statement)
    }

    constraints = {
        slug: constraint
        for slug, constraint in knowledge.constraints.items()
        if _matches(
            normalized,
            slug,
            f"con:{slug}",
            constraint.ref,
            constraint.statement,
        )
    }

    matched_exception_targets = {
        *(f"pol:{slug}" for slug in policies),
        *(f"con:{slug}" for slug in constraints),
    }
    exceptions = {
        slug: exception
        for slug, exception in knowledge.exceptions.items()
        if _matches(
            normalized,
            slug,
            f"exc:{slug}",
            exception.ref,
            exception.exception_to,
            exception.condition,
            exception.statement,
        )
        or exception.exception_to in matched_exception_targets
    }

    matched_references = {
        *(f"def:{slug}" for slug in definitions),
        *(f"pol:{slug}" for slug in policies),
        *(f"con:{slug}" for slug in constraints),
        *(f"exc:{slug}" for slug in exceptions),
    }
    relations = [
        relation
        for relation in knowledge.relations
        if _matches(
            normalized,
            relation.ref,
            relation.subject,
            relation.predicate,
            relation.object,
            relation.cardinality,
        )
        or relation.subject in matched_references
        or relation.object in matched_references
    ]

    return KnowledgeQueryResult(
        definitions,
        relations,
        policies,
        constraints,
        exceptions,
    )
