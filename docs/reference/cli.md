# CLI reference

`whub`と`wflow`の公開コマンド構文、引数、直接の挙動を定める。通常の実行contextは
`~/.whub`に固定する。実行順序・判断・復旧は各operationを参照する。

引数とoptionの全一覧は各commandの`--help`を正とする。

## Task workflow

| コマンド | 直接の挙動 |
|---|---|
| `wflow check [WORKFLOW]` | 指定したWorkflow、または組み込みTask Workflowを検証 |
| `wflow task --project <PROJECT> {ls,check,show}` | Taskの一覧・整合性・進捗を表示 |
| `wflow task --project <PROJECT> {init,update,acceptance,depends,plan}` | draftまたは進行中Taskを編集 |
| `wflow task --project <PROJECT> {transition,done,skip,log,accept}` | 状態・Step・log・受入結果を記録 |
| `wflow task --project <PROJECT> {log-update,log-delete,log-restore}` | 構造化Phase logを修正 |
| `wflow task --project <PROJECT> {interrupt,resume}` | Taskの割り込み・再開を操作 |
| `wflow task --project <PROJECT> complete <TASK-REF>` | Taskを完了しProjectの`docs/tasks/done/`へアーカイブ |

未完了TaskはHub側で管理する。Task操作では`--project`を明示する。Taskを跨ぐ運用は
[Task development](../operations/task-development.md)を参照する。

## ProjectとResource

| コマンド | 直接の挙動 |
|---|---|
| `whub init --workspace-root <PATH> [--force]` | 固定contextへworkspace rootを設定 |
| `whub ls` | Project名、Resource type、workspace pathを表示 |
| `whub status` | Resourceと登録済みworktreeの状態を診断 |
| `whub link` | manifestのlocal Resourceをworkspaceへsymlink |
| `whub cd <PROJECT> [--plain]` | local Resourceへ移動、またはremote ResourceへSSH接続 |
| `whub remote mount [PROJECT] [-a]` | remote hostをsshfs mountし、Resourceのworkspace symlinkを作成 |
| `whub remote unmount [--force]` | remote mountと対応するworkspace symlinkを撤去 |
| `whub remote run [--tty] <PROJECT> <COMMAND...>` | remote Resource直下でcommandを実行 |
| `whub remote cleanup-appledouble <PROJECT> [--apply]` | AppleDouble sidecarを検証し、指定時だけ削除 |
| `whub remote get <PATH-or-PROJECT:PATH>` | remoteの単一fileを`remote_files/`へ取得 |
| `whub remote put <LOCAL-NAME>` | 取得済みfileを元のremote pathへ書き戻し |
| `whub remote rm <LOCAL-NAME>` | 取得済みfileと対応metadataを削除 |

- `link`が`.gitignore`で管理するのは`.codegraph/`、`.DS_Store`、`._*`、`.AppleDouble/`だけとする。
- remote Resourceの参照・編集・実行・復旧は[Remote resource operation](../operations/remote.md)を参照する。

## Worktree

| コマンド | 直接の挙動 |
|---|---|
| `whub worktree create <PROJECT> <TTT>` | 未完了TaskからTask branchとpathを導出し、worktreeを登録・作成 |
| `whub worktree check` | 全登録のidentityとdiagnosticを読み取り専用で表示 |
| `whub worktree remove <PROJECT> <TTT>` | cleanかつ整合したTask worktreeと定義YAMLを削除 |
| `whub worktree pull-request <PROJECT> <TTT>` | Task branchをpushし、既存PRを返すかPRを作成 |
| `whub worktree merge <PROJECT> <TTT> --method {merge,squash,rebase}` | 一致するPRをmergeし、確認後にTask worktreeをcleanup |

- 詳細は[Worktree reference](worktree.md)、運用は[Worktree operation](../operations/worktree.md)を参照する。

## Agent

| コマンド | 直接の挙動 |
|---|---|
| `whub agent open <PROJECT> <TASK-ID> --auth <AUTH> [--auth <AUTH>]` | Agent設定を生成し、Taskのtmux sessionへ接続または新規作成 |
| `whub agent close <PROJECT> <TASK-ID>` | tmux sessionを停止し、未変更のHarness所有設定を削除 |
| `whub agent attention-hook` | stdinのCodex Hook eventをlocalhost Web appへ転送する。入力・通信・backendの失敗時も成功終了する |

詳細は[Agent harness operation](../operations/agent.md)を参照する。

## 作業支援

| コマンド | 直接の挙動 |
|---|---|
| `whub todo [-a] [COMMAND]` | 個人Todoの表示・追加・完了・削除 |
| `whub backlog <TEXT> [--project <PROJECT>]` | Projectの`docs/backlog.md`へ未整理memoを追記 |
| `whub codegraph` | `codegraph: true`のResourceでCodeGraphを初期化 |
| `whub shell-init [--shell zsh]` | shell functionと補完設定を出力 |

## Web appとRemote GUI session

| コマンド | 直接の挙動 |
|---|---|
| `whub app [--port <PORT>]` | managed Web app serverを起動 |
| `whub app dev` | HMRとAPI reloadを有効にしてWeb appを起動 |
| `whub app down` | managed Web app serverを停止 |
| `whub remote session <COMMAND>` | remote GUI sessionを予約・観測・削除 |

Web appはTask YAMLを更新しない。`/worktrees`は登録済みworktreeの読み取り専用表示とする。
Remote GUI sessionの運用は[Remote GUI session](../operations/session.md)を参照する。

## Operation release

| コマンド | 直接の挙動 |
|---|---|
| `whub release build --source <PATH>` | 開発checkoutからwheelをstagingへ作成 |
| `whub release deploy --source <PATH>` | build・verify・applyを同一release-idで順に実行 |
| `whub release verify <RELEASE-ID>` | staged releaseを検証しrelease recordを作成 |
| `whub release apply <RELEASE-ID>` | 検証済みreleaseをcurrentへ切り替え、appを再起動 |

releaseの順序・停止・復旧条件は[Operation release](../operations/releace.md)を参照する。
