# whub

複数PC・複数プロジェクトにまたがる開発作業を、単一マニフェストから管理する。
symlink・SSH・マニフェスト駆動のCLIにより、状態確認・移動・CodeGraph初期化を一元化する。

## 方針

- `~/.whub/manifest.yaml` が `project`、`resource`、接続情報の単一定義源
- `~/.whub/` にconfig・manifest・todo・releases・runtimeを集約する
- `remote get` したfileとそのメタデータはworkspace rootの`remote_files/`に置く
- ローカル`resource`はsymlink、リモート`resource`はsshfs mount（参照・編集）とSSH（実行）で操作する
- mountはhost単位に集約する。`host.mount_root`を`~/.whub/runtime/mounts/`配下へsshfsで1本だけ接続し、各`workspace_path`はそのmount内へのsymlinkとして張る
- `resource`の`path`は所属`host`の`mount_root`からの相対で表す。絶対pathの前置を各`resource`へ重複させず、`mount_root`の変更が単一の変更点になる
- 無引数mountの対象可否はsshfsの単位に合わせて`host.auto_mount`で決める。`resource`側にmount設定は持たせない
- Agentはworkspace rootから起動し、Project固有作業の前に対象rootの`AGENTS.md`を読む
- `whub codegraph`で`codegraph: true`な対象`resource`のCodeGraphを初期化

## Documentation

- [CLI reference](docs/reference/cli.md)
- [Manifest reference](docs/reference/manifest.md)
- [Worktree reference](docs/reference/worktree.md)
- [Agent harness operation](docs/operations/agent.md)
- [Architecture overview](docs/architecture/overview.md)
- [Development conventions](docs/development/conventions.md)
- [Architecture decisions](docs/ADR/)
- [Operations](docs/operations/)

## セットアップ

```sh
uv tool install .
whub init --workspace-root /path/to/workspace
source <(whub shell-init)   # .zshrc に追記
```

通常実行のcontextはcwdや`PWD`に関係なく`~/.whub`に固定される。初期化後、`~/.whub/`に`manifest.yaml`と必要に応じて`todos.yaml`を置く。開発・testで分離する場合は、CLI optionではなく`WhubContext`を直接構築・注入する。
