# ADR-0005: CLIサブコマンド体系

- **Status:** Accepted
- **Date:** 2026-06-19

## Context

workspace-hub CLIの日常操作とAgent設定配布に必要なサブコマンド体系を決める。

## Decision

以下のコマンドを採用する。

### セットアップ系

| コマンド | 説明 |
|----------|------|
| `whub link` | symlinkリソースからリンクを作成 |

### 日常操作系

| コマンド | 説明 |
|----------|------|
| `whub cd <resource>` | symlinkはローカルcd、remoteは対話SSH接続 |
| `whub status` | `boot: true`なsymlinkとremoteの状態一覧 |
| `whub status <resource> -e/-p` | リソースの状態文または優先度を更新 |

### ブートストラップ配布・診断系

| コマンド | 説明 |
|----------|------|
| `whub boot` | `boot: true`な全リソースとworkspace-hubにパッケージ内のAgent設定を配布 |
| `whub shell-init` | zsh関数と補完設定を出力 |

### whub cd の挙動

`whub cd`はリソース種別に応じて挙動を切り替える:

- **symlink**: ローカルのリソースパスにcd（シェル関数経由）
- **remote**: リモートホストにSSH接続し、対象パスにcd

ローカルcdには親シェルのディレクトリ変更が必要なため、`whub shell-init`が生成するシェル関数を`.zshrc`に追記する。

```sh
source <(whub shell-init)
```

Tab補完はマニフェストのリソース名一覧から生成する。

### whub status の挙動

引数なしでは`boot: true`なリソースを表示する。symlinkはローカル、remoteはSSH経由でディレクトリとGit差分件数を確認する。remoteは並列に確認し、いずれかが正常でなければ全件表示後に終了コード1を返す。

`-e`または`-p`を指定した場合は、対象リソースの状態文または優先度を`.whub/state.yaml`へ保存する。

### whub boot の挙動

workspace-hubと`boot: true`なリソースへAgent設定を配布する。remoteへの読込・書込・skills同期・CodeGraph初期化はSSHまたはrsyncを使う。対象単位の失敗は警告として表示し、後続対象を処理して終了コード0を返す。

### 廃止した候補

- **whub sync**: Git一括同期は不要。各リポジトリのgit操作は環境ごとに手動判断する
- **whub run**: 任意コマンド実行用の公開CLIは設けず、remote操作は内部APIとして利用する
- **whub mount / unmount**: remoteをローカルへマウントしない
- **whub init**: 現在は提供しない
- **whub context**: CLIコマンドとしては不要。将来的に自動化を検討

## Rationale

- `whub cd`を中心コマンドとすることで、リソース種別を意識せず統一的に移動できる
- `whub cd` → `claude`のワークフローにより、プロジェクトのCLAUDE.mdが自動で読み込まれる

## Consequences

- `whub shell-init`によるシェル関数の初期セットアップが必要
- Tab補完の実装にはCLIフレームワークの補完機能を利用する
- Git一括同期はCLIコマンドとして提供しない
