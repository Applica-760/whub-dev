# ADR-0011: Project固有Relation語彙

- **Status:** Superseded by ADR-0012
- **Date:** 2026-07-13

## Context

- Knowledge Relationの`predicate`はsnake_caseだけを検証し、未定義語や誤記を拒否できない
- `is_a`や`promotes_to`の意味が定義されていない
- Projectごとに必要なRelation語彙は異なる
- ADR-0010はKnowledgeの形式定義をPydanticモデルへ集約し、Knowledge YAMLによる形式の自己記述を避けている

## Decision

- 各Projectの`docs/knowledge.yaml`に必須の`relation_types`を置き、Project固有のRelation語彙を定義する
- Relation typeは`name`と`definition`だけを持つ
- PydanticモデルはRelation typeの形式と一意性、Relationはpredicate登録と参照先存在を検証する
- `relation_types`は形式定義ではなくProjectのドメイン語彙であり、形式のSSOTは引き続きPydanticモデルとする
- 必須フィールド追加に伴いKnowledge YAMLを`schema_version: 3`へ更新する

## Rationale

- YAML内の語彙レジストリならPythonコードとProject固有語彙を二重管理せずに未定義predicateを拒否できる
- schema versionを上げることで、Relation語彙を持たない旧形式を暗黙に受理しない

## Consequences

- 既存Knowledge YAMLへ利用中のRelation typeを定義する必要がある
- モデル・Service・CLI・OpenAPI型・テストをschema version 3へ更新する必要がある
- Relation typeの追加は各ProjectのKnowledge YAMLだけで完結する
- subject・object種別の制約は実データで必要性が確認された時に追加する
- `cardinality`の形式制約は本Decisionの対象外とする
