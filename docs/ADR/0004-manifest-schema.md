# ADR-0004: マニフェストスキーマ定義

- **Status:** Accepted
- **Date:** 2026-06-19

## Context

`manifest.yaml`（ADR-0001, ADR-0003）の具体的なスキーマを決める必要がある。全FR（Git同期・マウント・symlink・リモート操作・Agentルール配布）を単一ファイルで宣言的に定義する。

## Decision

以下のスキーマを採用する。

```yaml
version: "1"

# ── リモートホスト定義 ──
hosts:
  <host-key>:
    hostname: <string>       # required: IPまたはDNS名
    user: <string>           # required: SSHユーザ名
    identity_file: <string>  # required: SSH秘密鍵パス
    port: <int>              # optional, default: 22

# ── リソース定義 ──
resources:
  - name: <string>           # required: 一意な識別名
    path: <string>           # required: workspace-hub内の相対パス
    type: mount | symlink    # required

    # mount専用
    host: <host-key>         # mountの場合required: hostsのキーを参照
    remote_path: <string>    # mountの場合required: リモート側の絶対パス

    # symlink専用
    source: <string>         # symlinkの場合required: ローカルの絶対パス

    # 共通optional
    git:
      url: <string>          # GitリモートURL
      branch: <string>       # optional, default: デフォルトブランチ
    agent_rules: <bool>      # optional, default: false — Agentルール配布対象か
```

### 設計原則

1. **hostsは独立セクション** — 複数リソースが同一ホストを共有するため、DRYに参照する
2. **resourcesはフラットリスト** — `path`フィールドでツリー上の位置を決定。ネスト構造はパースの複雑性に見合わない
3. **gitフィールドはtype非依存** — symlinkもmountもGitリポジトリであり得る。mountの場合、git操作はリモート側で実行する（`hub exec`経由）
4. **agent_rulesフラグ** — FR-5配布対象をリソース単位で宣言する。デフォルトfalse

## Consequences

- CLIはresources配列をtype別にフィルタして各コマンド（link/mount/sync等）を実行する
- mount先のgit操作は`hub exec <host> git ...`で行い、ローカルからの直接pushは行わない
- 将来`type: git`（workspace-hub内に直接cloneする方式）が必要になった場合、typeの追加で対応可能
