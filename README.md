# workspace-hub

複数PC・複数プロジェクトにまたがる開発作業を、単一マニフェストから管理する。
symlink・SSH・マニフェスト駆動のCLIにより、状態確認・移動・Agent設定配布を一元化する。

## 方針

- `.whub/manifest.yaml` が単一定義源（SSOT）。リソースの追加・変更はここだけ
- ローカルリポジトリはsymlink、リモートリソースはSSH経由で操作する
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
| `whub cd <RESOURCE>` | symlinkへ移動、またはremoteで対話シェルを開始 |
| `whub status [RESOURCE] [-e TEXT] [-p PRIORITY]` | `boot: true`なリソースの状態一覧、またはリソース状態の編集 |
| `whub boot` | パッケージ内のAgent設定を`boot: true`な全プロジェクトとworkspace-hubへ配布 |
| `whub shell-init [--shell zsh]` | zsh関数＋補完設定を出力 |

## `.whub/manifest.yaml` の構造

```yaml
hosts:
  host-name:
    hostname: "..."
    user: "..."
    identity_file: "~/.ssh/id_rsa"

resources:
  symlinks:
    - name: my-project
      workspace_path: projects/my-project
      source: /path/to/repo
      boot: true
  remotes:
    - name: remote-project
      host: host-name
      path: /remote/path
      boot: true
```
