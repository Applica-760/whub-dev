# workspace-hub

複数PC・複数プロジェクトにまたがる開発作業を、単一マニフェストから管理する。
symlink・SSH・マニフェスト駆動のCLIにより、状態確認・移動・Agent設定配布を一元化する。

## 方針

- 用語・CLI設計方針は `docs/whub-concepts.md` を正とする
- `.whub/manifest.yaml` が `project`、`resource`、接続情報の単一定義源
- ローカル`resource`はsymlink、リモート`resource`はSSH経由で操作する
- whubパッケージ内の共通Agent設定を`whub boot`で対象`resource`に配布

## セットアップ

```sh
uv tool install -e .
source <(whub shell-init)   # .zshrc に追記
```

## コマンド一覧

| コマンド | 概要 |
|---|---|
| `whub status` | 接続状態、ヘルスチェック、git差分を表示 |
| `whub link` | manifest の symlink を一括作成（`.gitignore` も自動更新） |
| `whub cd <PROJECT\|RESOURCE>` | localならパス移動、remoteならSSH接続、移動先がなければ通知 |
| `whub todo` | `project`横断の単発アクションを管理 |
| `whub boot` | パッケージ内のAgent設定を`boot: true`な`resource`へ配布 |
| `whub shell-init [--shell zsh]` | zsh関数＋補完設定を出力 |

## `.whub/manifest.yaml` の構造

```yaml
version: "2"

hosts:
  host-name:
    hostname: "..."
    user: "..."
    identity_file: "~/.ssh/id_rsa"

projects:
  - name: workspace-hub

  - name: my-project
    resource:
      type: symlink
      workspace_path: projects/my-project
      source: /path/to/repo
      boot: true

  - name: remote-project
    resource:
      type: remote
      host: host-name
      path: /remote/path
      boot: true
```
