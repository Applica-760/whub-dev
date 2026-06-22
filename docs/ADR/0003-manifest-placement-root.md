# ADR-0003: マニフェストを`.whub/`に配置する

- **Status:** Accepted
- **Date:** 2026-06-19

## Context

単一YAMLマニフェスト（ADR-0001）の配置先を決める必要がある。候補はルート直下・config/・.hub/。

## Decision

`.whub/manifest.yaml`として配置する。

## Rationale

- whub固有の設定を`.whub/`へ集約できる
- 可変状態の`.whub/state.yaml`と配置規則を統一できる
- リポジトリルートの設定ファイル増加を抑えられる

## Consequences

- CLIはカレントディレクトリの`.whub/manifest.yaml`を読む
