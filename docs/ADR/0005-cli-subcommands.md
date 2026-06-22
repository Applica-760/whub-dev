# ADR-0005: CLIサブコマンド体系

- **Status:** Accepted
- **Date:** 2026-06-19

## Context

workspace-hub CLIのサブコマンド体系を決める必要がある。全FR（FR-1〜FR-7）をカバーしつつ、日常的に使うコマンドを最小限に保つ。

## Decision

以下のコマンドを採用する。

### セットアップ系

| コマンド | 対応FR | 説明 |
|----------|--------|------|
| `whub link` | FR-6, FR-7 | symlinkリソースからリンクを作成 |
| `whub mount [host] [--all]` | FR-2 | 省略時はauto_mount対象、host指定または--allで対象を拡張 |
| `whub unmount [host]` | FR-2 | 省略時は全mount、host指定時は対象ホストを解除 |

### 日常操作系

| コマンド | 対応FR | 説明 |
|----------|--------|------|
| `whub cd <resource>` | FR-3, FR-6, FR-7 | symlinkはローカルcd、mountは対話SSH接続 |
| `whub status [--check]` | FR-2 | 全リソースの状態一覧。--checkでSSH接続も確認 |

### ブートストラップ配布・診断系

| コマンド | 対応FR | 説明 |
|----------|--------|------|
| `whub boot` | FR-5 | boot=trueの全リソースとworkspace-hubにパッケージ内のAgent設定を配布 |
| `whub shell-init` | — | zsh関数と補完設定を出力 |
| `whub doctor` | — | 未実装の診断コマンド |

### whub cd の挙動

`whub cd`はリソースのtypeに応じて挙動を切り替える:

- **symlink**: ローカルのリソースパスにcd（シェル関数経由）
- **mount**: リモートホストにSSH接続し、remote_pathにcd

ローカルcdには親シェルのディレクトリ変更が必要なため、`whub shell-init`が生成するシェル関数を`.zshrc`に追記する。

```sh
source <(whub shell-init)
```

Tab補完はマニフェストのリソース名一覧から生成する。

### 廃止した候補

- **whub sync**: Git一括同期は不要。各リポジトリのgit操作は環境ごとに手動判断する
- **whub exec**: 現在は提供しない
- **whub ssh**: mountリソースへの`whub cd`が対話SSH接続を行う
- **whub init**: 現在は提供しない
- **whub context**: CLIコマンドとしては不要。将来的に自動化を検討

## Rationale

- `whub cd`を中心コマンドとすることで、リソース種別を意識せず統一的に移動できる
- `whub cd` → `claude`のワークフローにより、プロジェクトのCLAUDE.mdが自動で読み込まれる

## Consequences

- `whub shell-init`によるシェル関数の初期セットアップが必要
- Tab補完の実装にはCLIフレームワークの補完機能を利用する
- FR-1（Git一括同期）はCLIコマンドとして提供しない
