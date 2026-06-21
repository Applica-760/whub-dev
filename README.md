# workspace-hub

複数PC・複数プロジェクトにまたがる開発作業を、1つのディレクトリツリーとして統合する。
symlink・sshfsマウント・マニフェスト駆動のCLIにより、俯瞰・操作・AI連携を一元化する。

## 方針

- `manifest.yaml` が単一定義源（SSOT）。リソースの追加・変更はここだけ
- ローカルリポジトリは symlink、リモートは sshfs mount で参照（実体は移動しない）
- `.my-boot` に共通Agent設定（CLAUDE.md / AGENTS.md / MCP設定）を集約し、`whub boot deploy` で全プロジェクトに配布

## セットアップ

```sh
uv tool install -e .
source <(whub shell-init)   # .zshrc に追記
```

## コマンド一覧

| コマンド | 概要 |
|---|---|
| `whub link` | manifest の symlink を一括作成（`.gitignore` も自動更新） |
| `whub mount [HOST]` | sshfs でリモートをマウント（`--all` で auto_mount=false も含む） |
| `whub unmount [HOST]` | マウント解除 |
| `whub cd <RESOURCE>` | リソースへ移動（symlink→cd、mount→SSH） |
| `whub status` | 全リソースの状態一覧 |
| `whub boot deploy` | `.my-boot` のAgent設定を `boot: true` な全プロジェクトに配布 |
| `whub doctor` | ヘルスチェック（未実装） |
| `whub shell-init` | シェル関数＋補完設定を出力 |

## manifest.yaml の構造

```yaml
hosts:
  host-name:
    hostname: "..."
    user: "..."
    identity_file: "~/.ssh/id_rsa"
    auto_mount: true          # false だと whub mount --all が必要

resources:
  - name: my-project
    path: projects/my-project  # workspace-hub 内の相対パス
    type: symlink              # symlink | mount
    source: /path/to/repo      # symlink 用
    host: host-name            # mount 用
    remote_path: /remote/path  # mount 用
    git:
      url: git@github.com:...
      branch: main
    boot: true                 # true で whub boot deploy の対象
```
