# workspace-hub

複数PC・複数プロジェクトにまたがる開発作業を、単一マニフェストから管理する。
symlink・SSH・マニフェスト駆動のCLIにより、状態確認・移動・Agent設定配布を一元化する。

## 方針

- 用語・CLI設計方針は `docs/whub-concepts.md` を正とする
- `.whub/manifest.yaml` が `project`、`resource`、接続情報の単一定義源
- ローカル`resource`はsymlink、リモート`resource`はsshfs mount（参照・編集）とSSH（実行）で操作する
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
| `whub mount [PROJECT] [-a]` | remote `resource`をsshfsでツリーへマウント（`mount: false`は`-a`か名指しのみ） |
| `whub unmount [PROJECT] [--force]` | アンマウント（staleマウントは`--force`で強制解除） |
| `whub cd <PROJECT>` | localならパス移動、remoteならtmuxセッションへSSH接続（`--plain`で素シェル） |
| `whub run <PROJECT> <CMD...>` | remoteの`resource`直下でワンショット実行（終了コード引き継ぎ。対話は`cd`） |
| `whub todo` | `project`横断の単発アクションを管理 |
| `whub roadmap <PROJECT> <TEXT...>` | projectのroadmap末尾の未整理メモへ追記 |
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
      workspace_path: projects/remote-project  # sshfs mount先（必須）
      mount: false   # 任意: 無引数mountの対象から除外
      status: false  # 任意: statusの対象から除外
      boot: true
```
