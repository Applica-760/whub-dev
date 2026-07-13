"""Pydantic models and loader for Knowledge YAML."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

_KNOWLEDGE_ID_PATTERN = r"^(?:DEF|REL|POL|CON|EXC)-[0-9]+$"


class KnowledgeError(Exception):
    """Raised when Knowledge YAML cannot be loaded or validated."""


class KnowledgeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class KnowledgeEntry(KnowledgeModel):
    id: str


class KnowledgeDefinition(KnowledgeEntry):
    """用語が何であるかを表すDEFエントリ。"""

    id: str = Field(pattern=r"^DEF-[0-9]+$")
    name: str = Field(min_length=1)
    definition: str = Field(min_length=1)
    ref: str | None = Field(default=None, min_length=1)


class KnowledgeRelationType(KnowledgeModel):
    """Project固有のRelation predicate。"""

    name: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    definition: str = Field(min_length=1)


class KnowledgeRelation(KnowledgeEntry):
    """用語同士の関係を表すRELエントリ。"""

    id: str = Field(pattern=r"^REL-[0-9]+$")
    subject: str = Field(pattern=_KNOWLEDGE_ID_PATTERN)
    predicate: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    object: str = Field(pattern=_KNOWLEDGE_ID_PATTERN)
    cardinality: str | None = Field(default=None, min_length=1)
    ref: str | None = Field(default=None, min_length=1)


class KnowledgePolicy(KnowledgeEntry):
    """人間・Agentがどう運用するかを表すPOLエントリ。"""

    id: str = Field(pattern=r"^POL-[0-9]+$")
    statement: str = Field(min_length=1)
    ref: str | None = Field(default=None, min_length=1)


class KnowledgeConstraint(KnowledgeEntry):
    """データ・実装・CLIが必ず満たす性質を表すCONエントリ。"""

    id: str = Field(pattern=r"^CON-[0-9]+$")
    statement: str = Field(min_length=1)
    ref: str | None = Field(default=None, min_length=1)


class KnowledgeException(KnowledgeEntry):
    """PolicyまたはConstraintの例外を表すEXCエントリ。"""

    id: str = Field(pattern=r"^EXC-[0-9]+$")
    exception_to: str = Field(pattern=r"^(?:POL|CON)-[0-9]+$")
    condition: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    ref: str | None = Field(default=None, min_length=1)


class Knowledge(KnowledgeModel):
    schema_version: Literal[3]
    definitions: list[KnowledgeDefinition]
    relation_types: list[KnowledgeRelationType]
    relations: list[KnowledgeRelation]
    policies: list[KnowledgePolicy]
    constraints: list[KnowledgeConstraint]
    exceptions: list[KnowledgeException]

    @model_validator(mode="after")
    def _validate_ids_and_references(self) -> Knowledge:
        entries = [
            *self.definitions,
            *self.relations,
            *self.policies,
            *self.constraints,
            *self.exceptions,
        ]
        id_counts = Counter(entry.id for entry in entries)
        duplicates = sorted(
            entry_id for entry_id, count in id_counts.items() if count > 1
        )
        if duplicates:
            raise ValueError(f"duplicate knowledge ids: {', '.join(duplicates)}")

        relation_type_counts = Counter(item.name for item in self.relation_types)
        duplicate_relation_types = sorted(
            name for name, count in relation_type_counts.items() if count > 1
        )
        if duplicate_relation_types:
            raise ValueError(
                "duplicate relation type names: "
                f"{', '.join(duplicate_relation_types)}"
            )

        unknown_predicates = sorted(
            {relation.predicate for relation in self.relations}
            - set(relation_type_counts)
        )
        if unknown_predicates:
            raise ValueError(
                f"unknown relation predicates: {', '.join(unknown_predicates)}"
            )

        known_ids = set(id_counts)
        for relation in self.relations:
            unknown = sorted({relation.subject, relation.object} - known_ids)
            if unknown:
                raise ValueError(
                    f"relation '{relation.id}' references unknown knowledge ids: "
                    f"{', '.join(unknown)}"
                )

        exception_target_ids = {
            *(policy.id for policy in self.policies),
            *(constraint.id for constraint in self.constraints),
        }
        for exception in self.exceptions:
            if exception.exception_to not in exception_target_ids:
                raise ValueError(
                    f"exception '{exception.id}' references unknown policy or constraint: "
                    f"{exception.exception_to}"
                )
        return self


def load_knowledge(path: Path) -> Knowledge:
    try:
        data = yaml.safe_load(path.read_text())
        return Knowledge.model_validate(data)
    except (OSError, yaml.YAMLError, ValidationError) as error:
        raise KnowledgeError(
            f"failed to load Knowledge YAML: {path}: {error}"
        ) from error
