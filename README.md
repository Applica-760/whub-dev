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

## コマンド一覧

| コマンド | 概要 |
|---|---|
| `whub init --workspace-root PATH [--force]` | `~/.whub/config.toml` にworkspace rootを記録してcontextを初期化 |
| `whub ls` | project名、resource type、workspace pathを表示 |
| `whub status` | 接続状態、ヘルスチェック、git差分を表示 |
| `whub link` | manifest の symlink を一括作成し、whub runtime metadata のみを `.gitignore` へ自動追加 |
| `whub remote mount [PROJECT] [-a]` | 対象`resource`のhostをsshfsでマウントし`workspace_path`のsymlinkを張る（`auto_mount: false`のhostは`-a`か名指しのみ） |
| `whub remote unmount [--force]` | 全hostのマウントを解除し`workspace_path`のsymlinkも撤去（staleマウントは`--force`で強制解除） |
| `whub cd <PROJECT>` | localならパス移動、remoteならtmuxセッションへSSH接続（`--plain`で素シェル） |
| `whub remote run <PROJECT> <CMD...>` | remoteの`resource`直下でワンショット実行（終了コード引き継ぎ。対話は`cd`） |
| `whub remote cleanup-appledouble <PROJECT> [--apply]` | remote host上で検証済みAppleDouble sidecarを一覧表示し、`--apply`時だけ削除 |
| `whub remote session <COMMAND>` | remote GUI sessionの予約・command handoff・状態確認・ログ取得・削除 |
| `whub agent open <PROJECT> <TASK-ID> --auth <AUTH>` | 登録済みTask worktreeのAgent設定を生成し、tmux sessionへattachまたは新規起動 |
| `whub agent close <PROJECT> <TASK-ID>` | Agent tmux sessionを停止し、whub所有の未変更設定を除去 |
| `whub remote get <PATH>` | remoteの単一fileをworkspace rootの`remote_files/`へ取得 |
| `whub remote put <LOCAL_NAME>` | `whub remote get`した`remote_files/`配下のfileを取得元のremote fileへ書き戻す |
| `whub remote rm <LOCAL_NAME>` | 管理済みの`remote_files/`配下fileと対応メタデータを削除 |
| `whub todo` | `project`横断の単発アクションを管理 |
| `whub backlog <TEXT> [--project PROJECT]` | projectのbacklog末尾の未整理メモへ追記（既定は`whub-dev`） |
| `whub codegraph` | `codegraph: true`な`resource`のCodeGraphを初期化 |
| `whub shell-init [--shell zsh]` | zsh関数＋補完設定を出力 |
| `whub release build --source PATH` | 開発checkoutからoperation releaseのwheelをstagingへ作成 |
| `whub release verify RELEASE_ID` | staging wheelとvenvを検証してrelease recordを作成 |
| `whub release apply RELEASE_ID` | 検証済みreleaseをcurrentへ切替え、appを再起動 |

`whub ls`はmanifestの接続情報を公開せず、Project解決に必要な情報だけを表示する。

```sh
whub ls
```

## Operation release

開発checkoutをoperation releaseへ反映するには、clean worktreeをsourceとして順に実行する。release操作だけは、古い`current` releaseに依存しないよう開発checkoutのPython moduleを実行する。通常の`whub`・`wflow`操作はPATH上のCLIを使う。

```sh
source=/path/to/whub
PYTHONPATH="$source/src" uv run --project "$source" python -m whub release build --source "$source"
PYTHONPATH="$source/src" uv run --project "$source" python -m whub release verify <release-id>
PYTHONPATH="$source/src" uv run --project "$source" python -m whub release apply <release-id>
```

各段階の停止・復旧・検証条件は[operation release contract](docs/operations/releace.md)に従う。

## Task Workflow

新規・未完了の個別作業はTask YAMLをSSOTとし、完了済みMarkdown Taskは履歴として扱う。対話・承認の詳細は`task-planning` Skillに従う。
表内で`wflow task`を省略したコマンドは、すべてそのサブコマンドを表す。
`wflow task`の既定Projectは`whub-dev`とする。別Projectを操作する場合は`wflow task --project PROJECT COMMAND`を使う。

| 区分 | コマンド |
|---|---|
| 確認 | `wflow task ls` / `check TASK` / `show TASK` |
| 新規作成 | `wflow task init "タイトル" "目的" --approach "方針"` |
| 依存関係 | `depends add TASK DEPENDENCY` / `depends delete TASK DEPENDENCY`（draftのみ） |
| 計画追加・承認 | `plan insert TASK "Step"` → `check` → `transition TASK approve_plan --actor user` |
| 進行記録 | `done` / `skip --reason` / `log TASK PPP --log` |
| 計画編集 | `plan update` / `plan insert` / `plan delete` / `plan restore`（draft・in_progressのみ） |
| 割り込み | `interrupt PARENT CHILD --reason "…"` / `resume PARENT` |
| 受入・完了 | `accept` / `complete TASK --result "…"` |

`wflow task complete`はTaskの完了記録と`docs/tasks/done`へのアーカイブを一操作で行う。

## Remote GUI session

予約・command handoff・状態確認・削除の手順は[Remote GUI session](docs/operations/session.md)に従う。
