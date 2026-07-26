# ADR-0013: Knowledge subsystemの廃止

- **Status:** Accepted
- **Date:** 2026-07-26
- **Supersedes:** ADR-0010, ADR-0012

## Context

Knowledge YAMLは用語、規約、実装制約を独自schemaで集約し、CLIとWeb appで照会していた。一方で、内容はREADME、ADR、実装、テスト、runbookにも重複し、利用者が通常参照するソフトウェア文書の構成から外れていた。

## Decision

Knowledge YAML、`whub knowledge`、Knowledge API、Web画面、専用モデル・service・テストを廃止する。互換API、移行用の二重管理、local cacheは設けない。

現在の情報は次の構成で管理する。

- `README.md`: 概要、導入、主要な利用方法
- `docs/reference/`: CLIとmanifestの参照
- `docs/architecture/`: 現在の構造と不変条件
- `docs/ADR/`: 設計判断の履歴
- `docs/operations/`: 運用runbook
- `docs/development/`: 開発規約

## Consequences

- 文書と実装を同じ変更で更新する。
- テスト可能な仕様はテストを実装保証とし、設計判断はADRへ記録する。
- 過去のTaskとADRのKnowledgeへの言及は履歴として保持する。
