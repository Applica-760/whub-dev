# ADR-0003: マニフェストをリポジトリルート直下に配置する

- **Status:** Accepted
- **Date:** 2026-06-19

## Context

単一YAMLマニフェスト（ADR-0001）の配置先を決める必要がある。候補はルート直下・config/・.hub/。

## Decision

`manifest.yml` としてリポジトリルート直下に配置する。

## Rationale

- workspace-hubの最も重要な定義ファイルであり、即座に見つかるべき
- CLIもAIも追加のパス解決なしでアクセスできる
- ルートの肥大化は.gitignore等と同列で実質問題にならない

## Consequences

- CLIはカレントディレクトリの `manifest.yml` を読む規約とする
