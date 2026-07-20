# ADR-0012: Knowledgeの安定slug参照

- **Status:** Accepted
- **Date:** 2026-07-20
- **Supersedes:** ADR-0011

## Context

- `DEF-001`等の連番は内容を表さず、削除後の欠番や最大番号の再利用を生む
- Relation typeは自然言語の意味を機械的に保証せず、登録Service・CLIを維持する負担がある
- KnowledgeはGit管理する小規模なproject内データであり、グラフDBを必要とする規模・照会要件ではない

## Decision

- Knowledge YAMLを`schema_version: 4`とする
- Definition・Policy・Constraint・Exceptionはカテゴリ別mappingとし、`^[a-z][a-z0-9_]*$`形式のslugをkeyにする
- 参照は`def:project`・`con:knowledge_updates_via_cli`等のカテゴリ修飾形式にする
- entryの数値IDと`id` fieldを廃止する
- Relationは`subject`・`predicate`・`object`の複合キーで一意にし、数値IDを持たせない
- `relation_types`とそのService・CLIを廃止し、`predicate`自身をslug形式に制約する
- slugはentryが存在する間は変更せず、物理削除後の再利用は許容する
- tombstone・rename CLI・グラフDBは導入しない

## Rationale

- 意味のあるslugならAgentと人間が参照先をID解決なしで理解できる
- カテゴリ修飾により、カテゴリ間の同名slugを許容しながら参照先を一意にできる
- Relationの複合キーは現行の参照・追加・削除要件を満たし、独立IDを不要にする
- 更新頻度が低いため、削除履歴を永続化する複雑さよりYAMLと操作の単純さを優先する

## Consequences

- addはentryカテゴリでslug、Relationでsubject・predicate・objectを明示する
- rmは参照中のentryを拒否し、Relationは複合キーで削除する
- predicateの意味的妥当性はCLIではなく、Knowledgeを参照するAgentが判断する
- schema v3との読込互換は持たず、既存Knowledgeをschema v4へ移行する
