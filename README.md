# whub

複数PC・複数プロジェクトにまたがる開発作業を、単一マニフェストから管理する。
symlink・SSH・マニフェスト駆動のCLIにより、状態確認・移動・CodeGraph初期化を一元化する。

## 方針

- 用語・CLI設計・運用規則は `docs/knowledge.yaml` を正とする
- `~/.whub/manifest.yaml` が `project`、`resource`、接続情報の単一定義源
- `~/.whub/` にconfig・manifest・todo・downloads・releases・runtimeを集約する
- ローカル`resource`はsymlink、リモート`resource`はsshfs mount（参照・編集）とSSH（実行）で操作する
- Agentはworkspace rootから起動し、Project固有作業の前に対象rootの`AGENTS.md`を読む
- `whub codegraph`で`codegraph: true`な対象`resource`のCodeGraphを初期化

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
| `whub link` | manifest の symlink を一括作成（`.gitignore` も自動更新） |
| `whub mount [PROJECT] [-a]` | remote `resource`をsshfsでツリーへマウント（`mount: false`は`-a`か名指しのみ） |
| `whub unmount [PROJECT] [--force]` | アンマウント（staleマウントは`--force`で強制解除） |
| `whub cd <PROJECT>` | localならパス移動、remoteならtmuxセッションへSSH接続（`--plain`で素シェル） |
| `whub run <PROJECT> <CMD...>` | remoteの`resource`直下でワンショット実行（終了コード引き継ぎ。対話は`cd`） |
| `whub session <COMMAND>` | remote GUI sessionの予約・command handoff・状態確認・ログ取得・削除 |
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

開発checkoutをoperation releaseへ反映するには、clean worktreeをsourceとして順に実行する。

```sh
whub release build --source /path/to/whub
whub release verify <release-id>
whub release apply <release-id>
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
| 計画変更 | `transition TASK request_plan_change --actor agent --reason "…"` → `plan delete` / `plan insert` → 再承認 |
| 割り込み | `interrupt PARENT CHILD --reason "…"` / `resume PARENT` |
| 受入・完了 | `accept` / `complete TASK --result "…"` |

`wflow task complete`はTaskの完了記録と`docs/tasks/done`へのアーカイブを一操作で行う。

## Remote GUI session

Mac側でrunを予約する。remote `resource`のmountは不要。

```sh
whub session reserve <PROJECT> [--task TASK-NNN]
```

表示されたlauncher commandを、対象Project直下のLinux GUI terminalで実行する。launcherはGUI環境を継承した専用tmux sessionを開始し、再実行時は生存中のsessionへ再attachする。

```sh
bash .whub/session-launcher.sh <RUN_ID>
```

Mac側で用意した複雑なcommandは、既存runと単一行の目的を指定してstdinから渡す。quoted heredocを使うと、command内の変数やquoteをMac側shellで展開せずに送信できる。remote `resource`のmountは不要。

```sh
whub session handoff <PROJECT> <RUN_ID> --purpose "Rerun probe" <<'WHUB_COMMAND'
PATH="$PWD/.venv/bin:$PATH" uv run python probe.py \
  --name 'complex value'
WHUB_COMMAND
```

Linux GUI側では対象Projectの`.whub/handoff/commands.md`を開く。先頭の最新entryにはrun固有の2手順があり、Step 1のlauncher commandをGUI terminalでcopy実行して対象tmux sessionへ入り、Step 2のworkload commandをtmux内でcopy実行する。whubはMarkdown内のcommandを解析・自動実行しない。fileはProjectごとに1つで履歴を保持し、`session clean`でも削除しない。

Mac側から状態とtranscriptを確認する。

```sh
whub session ls <PROJECT>
whub session show <PROJECT> <RUN_ID>
whub session logs <PROJECT> <RUN_ID> [--pane PANE_OR_WINDOW]
whub session logs <PROJECT> <RUN_ID> --follow [--pane PANE_OR_WINDOW]
```

`--follow`の切断やtmuxのdetachはremote処理を停止しない。停止は対象processへ明示し、`show`で終了code・signalと`completed`・`failed`・`interrupted`を確認する。`pending`または終了済みrunのdescriptor・metadata・transcriptはrun単位で削除できるが、`running` runの削除は拒否される。

```sh
whub session clean <PROJECT> <RUN_ID>
```

## `~/.whub/manifest.yaml` の構造

```yaml
version: "2"

hosts:
  host-name:
    hostname: "..."
    user: "..."
    identity_file: "~/.ssh/id_rsa"

projects:
  - name: whub-dev
    resource:
      type: symlink
      workspace_path: whub-dev
      source: /path/to/whub
      codegraph: true

  - name: remote-project
    resource:
      type: remote
      host: host-name
      path: /remote/path
      workspace_path: projects/remote-project  # sshfs mount先（必須）
      mount: false   # 任意: 無引数mountの対象から除外
      status: false  # 任意: statusの対象から除外
      codegraph: true
```
