# ADR-0004: マニフェストスキーマ定義

- **Status:** Accepted
- **Date:** 2026-06-19

## Context

`.whub/manifest.yaml`（ADR-0001, ADR-0003）の具体的なスキーマを決める必要がある。

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
  symlinks:
    - name: <string>             # required: 全リソース内で一意
      workspace_path: <string>   # required: workspace-hub内の相対パス
      source: <string>           # required: ローカルの絶対パス
      git:
        url: <string>            # required when git is present
        branch: <string>         # optional
      boot: <bool>               # optional, default: false

  remotes:
    - name: <string>             # required: 全リソース内で一意
      host: <host-key>           # required: hostsのキーを参照
      path: <string>             # required: リモート側の絶対パス
      git:
        url: <string>            # required when git is present
        branch: <string>         # optional
      boot: <bool>               # optional, default: false
```

### 設計原則

1. **hostsは独立セクション** — 複数リソースが同一ホストを共有するため、DRYに参照する
2. **symlinkとremoteは独立モデル** — ローカルパスとリモートパスの意味を混在させない
3. **remoteはローカルツリーに配置しない** — `host`と`path`を使ってSSH経由で操作する
4. **gitフィールドは種別非依存** — symlinkとremoteの状態表示でGit差分件数を取得する
5. **bootフラグ** — Agent設定の配布対象をリソース単位で宣言する。デフォルトfalse

### 検証規則

- 未定義フィールドは拒否する
- `workspace_path`は絶対パスと`..`によるworkspace外参照を拒否する
- symlinkの`source`は絶対パスのみ受理する
- remoteの`path`は`~`を含まないPOSIX絶対パスのみ受理する
- remoteの`host`は`hosts`に存在しなければならない
- symlinkとremoteを通してリソース名の重複を拒否する

## Consequences

- CLIは`resources.symlinks`と`resources.remotes`を使ってlink・cd・status・bootを実行する
- mount、unmount、SSHFSおよび旧フラットスキーマとの互換処理は提供しない
- Git操作コマンドは現時点で提供しない
