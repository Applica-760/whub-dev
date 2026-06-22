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

### 日常操作系

| コマンド | 対応FR | 説明 |
|----------|--------|------|
| `whub cd <resource>` | FR-3, FR-6, FR-7 | symlinkはローカルcd、remoteは対話SSH接続 |
| `whub run [--tty] <resource> <command> [arg]...` | FR-3 | remoteの対象パスでコマンドを実行 |
| `whub status` | FR-2 | symlinkとremoteの状態一覧 |

### ブートストラップ配布・診断系

| コマンド | 対応FR | 説明 |
|----------|--------|------|
| `whub boot` | FR-5 | boot=trueの全リソースとworkspace-hubにパッケージ内のAgent設定を配布 |
| `whub shell-init` | — | zsh関数と補完設定を出力 |
| `whub doctor` | — | 未実装の診断コマンド |

### whub cd の挙動

`whub cd`はリソースのtypeに応じて挙動を切り替える:

- **symlink**: ローカルのリソースパスにcd（シェル関数経由）
- **remote**: リモートホストにSSH接続し、対象パスにcd

ローカルcdには親シェルのディレクトリ変更が必要なため、`whub shell-init`が生成するシェル関数を`.zshrc`に追記する。

```sh
source <(whub shell-init)
```

Tab補完はマニフェストのリソース名一覧から生成する。

### whub run の挙動

`whub run`はremoteリソース専用とし、対象パスへ移動してから引数境界を維持してコマンドを実行する。標準入出力と終了コードはSSH経由で伝達し、対話コマンドでは`--tty`を指定する。

### 採用した名称

- **whub run**: remoteリソース上でコマンドを実行する
- **whub cd**: remoteリソースへの対話SSH接続を行う

### 廃止した候補

- **whub sync**: Git一括同期は不要。各リポジトリのgit操作は環境ごとに手動判断する
- **whub init**: 現在は提供しない
- **whub context**: CLIコマンドとしては不要。将来的に自動化を検討

## Rationale

- `whub cd`を中心コマンドとすることで、リソース種別を意識せず統一的に移動できる
- `whub cd` → `claude`のワークフローにより、プロジェクトのCLAUDE.mdが自動で読み込まれる

## Consequences

- `whub shell-init`によるシェル関数の初期セットアップが必要
- Tab補完の実装にはCLIフレームワークの補完機能を利用する
- FR-1（Git一括同期）はCLIコマンドとして提供しない
