# CLI reference

`whub`の公開コマンド構文、引数、直接の挙動を定める。通常の実行contextは
`~/.whub`に固定する。実行順序・判断・復旧は各operationを参照する。

引数とoptionの全一覧は各commandの`--help`を正とする。

## Task workflow

| コマンド | 直接の挙動 |
|---|---|
| `whub task --project <PROJECT> init <TITLE> <OBJECTIVE>` | draft TaskのYAML/Markdown pairを作成 |
| `whub task --project <PROJECT> check <TASK-REF>` | active/archiveのTask pairを検証 |
| `whub task --project <PROJECT> start <TASK-REF>` | 依存が完了したdraft Taskを開始 |
| `whub task --project <PROJECT> depends {add,delete} <TASK-REF> <TASK-REF>` | Task依存を更新 |
| `whub task --project <PROJECT> {interrupt,resume}` | Taskの割り込み・再開を操作 |
| `whub task --project <PROJECT> {complete,cancel} <TASK-REF>` | terminal stateへ遷移しProjectの`docs/tasks/done/`へpairをarchive |
| `whub task --project <PROJECT> log <TASK-REF> --log <JSON>` | Markdownへ構造化ログを追記 |

未完了TaskはHub側の`flow/tasks/<project>/`で管理する。`docs/tasks/done/`だけを履歴として
読み、旧`docs/tasks/`のYAMLは参照しない。Task操作では`--project`を明示する。状態遷移の
actor指定は公開しない。Taskを跨ぐ運用は
[Task development](../operations/task-development.md)を参照する。

## ProjectとResource

| コマンド | 直接の挙動 |
|---|---|
| `whub init --workspace-root <PATH> [--force]` | 固定contextへworkspace rootを設定 |
| `whub ls` | Project名、Resource type、workspace pathを表示 |
| `whub status` | Resourceの状態を診断 |
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

## Agent

| コマンド | 直接の挙動 |
|---|---|
| `whub agent open <PROJECT> <TASK-ID> --auth <AUTH> [--auth <AUTH>]` | Agent設定を生成し、Taskのtmux sessionへ接続または新規作成。remote Resourceはhost内で起動しSSHでattachする |
| `whub agent close <PROJECT> <TASK-ID>` | tmux sessionを停止し、未変更のHarness所有設定を削除。remote Resourceの生成物もhost上でcleanupする |
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

Web appはTask YAMLを更新しない。Terminalは稼働中Agent sessionだけを表示する。
Remote GUI sessionの運用は[Remote GUI session](../operations/session.md)を参照する。

## Operation release

| コマンド | 直接の挙動 |
|---|---|
| `whub release build --source <PATH>` | 開発checkoutからwheelをstagingへ作成 |
| `whub release deploy --source <PATH>` | build・verify・applyを同一release-idで順に実行 |
| `whub release verify <RELEASE-ID>` | staged releaseを検証しrelease recordを作成 |
| `whub release apply <RELEASE-ID>` | 検証済みreleaseをcurrentへ切り替え、appを再起動 |

releaseの順序・停止・復旧条件は[Operation release](../operations/releace.md)を参照する。
