# ADR-0002: CLIツールの実装言語をPythonとする

- **Status:** Accepted
- **Date:** 2026-06-19

## Context

workspace-hubのCLIツール（マニフェスト解釈・ローカルリンク・SSH経由のリモート操作等）の実装言語選定。

## Decision

Pythonで実装する。

## Rationale

- 主処理は「YAMLパース→外部コマンド実行→構造化出力」であり、シェルスクリプト単体ではYAMLパースと構造化出力が弱い
- Node.jsとPythonの間に技術的な優劣はなく、ユーザーがPythonに慣れている
- Pythonはプロジェクト内で他の用途でも使用するため、追加の依存にならない
- 標準ライブラリ、Click、PyYAML、Pydanticで必要な処理を実装できる

## Consequences

- パッケージ管理はpyproject.tomlで行う
- CLI構築にはClickを使用する
