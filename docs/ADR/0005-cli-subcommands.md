# ADR-0005: CLIサブコマンド体系

- **Status:** Accepted
- **Date:** 2026-06-19

## Context

workspace-hub CLIのサブコマンド体系を決める必要がある。全FR（FR-1〜FR-7）をカバーしつつ、日常的に使うコマンドを最小限に保つ。

## Decision

以下の6コマンドを採用する。

### セットアップ系

| コマンド | 対応FR | 説明 |
|----------|--------|------|
| `hub link` | FR-6, FR-7 | manifest.yamlのsymlinkエントリからリンクを作成 |
| `hub mount [host]` | FR-2 | ホスト単位でsshfsマウント（省略時は全ホスト） |
| `hub unmount [host]` | FR-2 | マウント解除 |

### 日常操作系

| コマンド | 対応FR | 説明 |
|----------|--------|------|
| `hub cd <resource> [command]` | FR-3, FR-6, FR-7 | リソース名で移動。symlinkはローカルcd、mountはSSH接続。command指定で非対話実行 |
| `hub status` | FR-2 | 全リソースの状態一覧 |

### ルール配布・診断系

| コマンド | 対応FR | 説明 |
|----------|--------|------|
| `hub rules deploy` | FR-5 | agent_rules=trueの全リソースに.my-bootのルールを配布 |
| `hub doctor` | — | 設定の整合性チェック（リンク切れ、接続不能、manifest構文等） |

### hub cd の挙動

`hub cd`はリソースのtypeに応じて挙動を切り替える:

- **symlink**: ローカルのリソースパスにcd（シェル関数経由）
- **mount**: リモートホストにSSH接続し、remote_pathにcd

ローカルcdには親シェルのディレクトリ変更が必要なため、`hub shell-init`が生成するシェル関数を`.zshrc`に追記する。

```sh
eval "$(hub shell-init)"
```

Tab補完はマニフェストのリソース名一覧から生成する。

### 廃止した候補

- **hub sync**: Git一括同期は不要。各リポジトリのgit操作は環境ごとに手動判断が必要（同一リモートを複数環境が参照するため）
- **hub exec**: `hub cd`に統合。非対話コマンド実行は`hub cd <resource> "command"`で対応
- **hub ssh**: `hub cd`に統合。mountリソースへの`hub cd`がSSH接続を行う
- **hub init**: linkとmountの実行頻度が異なるため、まとめる利点がない
- **hub context**: CLIコマンドとしては不要。将来的にsync連動で自動化を検討

## Rationale

- `hub cd`を中心コマンドとすることで、リソース種別を意識せず統一的に移動できる
- `hub cd` → `claude`のワークフローにより、プロジェクトのCLAUDE.mdが自動で読み込まれ、FR-4（AIコンテキスト自動注入）の一部を自然に実現する
- コマンド数を6つに絞ることで学習コストを最小化する

## Consequences

- `hub shell-init`の実装とシェル関数の初期セットアップが必要
- Tab補完の実装にはCLIフレームワークの補完機能を利用する
- FR-1（Git一括同期）はCLIコマンドとしては提供せず、`hub rules deploy`と手動git操作でカバーする
