# workspace-hub

複数PC・複数プロジェクトにまたがる開発作業を、1つのディレクトリツリーとして統合する。
symlink・sshfsマウント・マニフェスト駆動のCLIにより、俯瞰・操作・AI連携を一元化する。

## 方針

- `.whub/manifest.yaml` が単一定義源（SSOT）。リソースの追加・変更はここだけ
- ローカルリポジトリは symlink、リモートは sshfs mount で参照（実体は移動しない）
- whubパッケージ内の共通Agent設定を`whub boot`で対象プロジェクトに配布

## セットアップ

```sh
uv tool install -e .
source <(whub shell-init)   # .zshrc に追記
```

## コマンド一覧

| コマンド | 概要 |
|---|---|
| `whub link` | manifest の symlink を一括作成（`.gitignore` も自動更新） |
| `whub mount [HOST]` | sshfsでマウント（HOST省略時は`auto_mount: true`、`--all`で全対象） |
| `whub unmount [HOST]` | マウント解除 |
| `whub cd <RESOURCE>` | リソースへ移動（symlink→cd、mount→SSH） |
| `whub status [--check]` | 全リソースの状態一覧（`--check`でリモート接続も確認） |
| `whub boot` | パッケージ内のAgent設定を`boot: true`な全プロジェクトとworkspace-hubへ配布 |
| `whub doctor` | ヘルスチェック（未実装） |
| `whub shell-init [--shell zsh]` | zsh関数＋補完設定を出力 |

## `.whub/manifest.yaml` の構造

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
    boot: true                 # true で whub boot の対象
```
