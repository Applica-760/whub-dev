"""Pydantic models and loader for Knowledge YAML."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

_SLUG_PATTERN = r"^[a-z][a-z0-9_]*$"
_REFERENCE_PATTERN = rf"^(?:def|pol|con|exc):{_SLUG_PATTERN[1:-1]}$"
_EXCEPTION_TARGET_PATTERN = rf"^(?:pol|con):{_SLUG_PATTERN[1:-1]}$"

KnowledgeSlug = Annotated[str, Field(pattern=_SLUG_PATTERN)]
KnowledgeReference = Annotated[str, Field(pattern=_REFERENCE_PATTERN)]
ExceptionTarget = Annotated[str, Field(pattern=_EXCEPTION_TARGET_PATTERN)]


class KnowledgeError(Exception):
    """Raised when Knowledge YAML cannot be loaded or validated."""


class KnowledgeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class KnowledgeDefinition(KnowledgeModel):
    """用語が何であるかを表すDEFエントリ。"""

    name: str = Field(min_length=1)
    definition: str = Field(min_length=1)
    ref: str | None = Field(default=None, min_length=1)


class KnowledgeRelation(KnowledgeModel):
    """用語同士の関係を表すRELエントリ。"""

    subject: KnowledgeReference
    predicate: KnowledgeSlug
    object: KnowledgeReference
    cardinality: str | None = Field(default=None, min_length=1)
    ref: str | None = Field(default=None, min_length=1)


class KnowledgePolicy(KnowledgeModel):
    """人間・Agentがどう運用するかを表すPOLエントリ。"""

    statement: str = Field(min_length=1)
    ref: str | None = Field(default=None, min_length=1)


class KnowledgeConstraint(KnowledgeModel):
    """データ・実装・CLIが必ず満たす性質を表すCONエントリ。"""

    statement: str = Field(min_length=1)
    ref: str | None = Field(default=None, min_length=1)


class KnowledgeException(KnowledgeModel):
    """PolicyまたはConstraintの例外を表すEXCエントリ。"""

    exception_to: ExceptionTarget
    condition: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    ref: str | None = Field(default=None, min_length=1)


class Knowledge(KnowledgeModel):
    schema_version: Literal[4]
    definitions: dict[KnowledgeSlug, KnowledgeDefinition]
    relations: list[KnowledgeRelation]
    policies: dict[KnowledgeSlug, KnowledgePolicy]
    constraints: dict[KnowledgeSlug, KnowledgeConstraint]
    exceptions: dict[KnowledgeSlug, KnowledgeException]

    @model_validator(mode="after")
    def _validate_references(self) -> Knowledge:
        relation_counts = Counter(
            (relation.subject, relation.predicate, relation.object)
            for relation in self.relations
        )
        duplicate_relations = sorted(
            relation for relation, count in relation_counts.items() if count > 1
        )
        if duplicate_relations:
            rendered = ", ".join(" ".join(relation) for relation in duplicate_relations)
            raise ValueError(f"duplicate knowledge relations: {rendered}")

        known_references = {
            *(f"def:{slug}" for slug in self.definitions),
            *(f"pol:{slug}" for slug in self.policies),
            *(f"con:{slug}" for slug in self.constraints),
            *(f"exc:{slug}" for slug in self.exceptions),
        }
        for relation in self.relations:
            unknown = sorted({relation.subject, relation.object} - known_references)
            if unknown:
                raise ValueError(
                    "relation "
                    f"'{relation.subject} {relation.predicate} {relation.object}' "
                    "references unknown knowledge entries: "
                    f"{', '.join(unknown)}"
                )

        exception_targets = {
            *(f"pol:{slug}" for slug in self.policies),
            *(f"con:{slug}" for slug in self.constraints),
        }
        for slug, exception in self.exceptions.items():
            if exception.exception_to not in exception_targets:
                raise ValueError(
                    f"exception 'exc:{slug}' references unknown policy or constraint: "
                    f"{exception.exception_to}"
                )
        return self


class _UniqueKeyLoader(yaml.SafeLoader):
    """YAML loader that rejects duplicate mapping keys."""


def _construct_unique_mapping(
    loader: _UniqueKeyLoader,
    node: yaml.MappingNode,
    deep: bool = False,
) -> dict[object, object]:
    mapping: dict[object, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key: {key}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def load_knowledge(path: Path) -> Knowledge:
    try:
        data = yaml.load(path.read_text(), Loader=_UniqueKeyLoader)
        return Knowledge.model_validate(data)
    except (OSError, yaml.YAMLError, ValidationError) as error:
        raise KnowledgeError(
            f"failed to load Knowledge YAML: {path}: {error}"
        ) from error
