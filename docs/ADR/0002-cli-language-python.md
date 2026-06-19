# ADR-0002: CLIツールの実装言語をPythonとする

- **Status:** Accepted
- **Date:** 2026-06-19

## Context

workspace-hubのCLIツール（マニフェスト解釈・Git同期・マウント・リモート操作等）の実装言語選定。

## Decision

Pythonで実装する。

## Rationale

- 全FRの本質は「YAMLパース→外部コマンド実行→構造化出力」であり、シェルスクリプト単体ではYAMLパースと構造化出力が弱い
- Node.jsとPythonの間に技術的な優劣はなく、ユーザーがPythonに慣れている
- Pythonはプロジェクト内で他の用途でも使用するため、追加の依存にならない
- 標準ライブラリ（subprocess, argparse）とPyYAMLで必要十分

## Consequences

- パッケージ管理はpyproject.tomlで行う
- CLI構築にはargparseまたはclickを使用
