# Remote GUI session

Mac側で予約したrunを、Linux GUI環境の専用tmux sessionで実行し、Mac側から状態とtranscriptを確認する手順を定義する。

## 予約

Mac側でrunを予約する。remote `resource`のmountは不要。

```sh
whub remote session reserve <PROJECT> [--task TASK-NNN]
```

表示されたlauncher commandを、対象Project直下のLinux GUI terminalで実行する。launcherはGUI環境を継承した専用tmux sessionを開始し、再実行時は生存中のsessionへ再attachする。

```sh
bash .whub/session-launcher.sh <RUN_ID>
```

## Command handoff

Mac側で用意した複雑なcommandは、既存runと単一行の目的を指定してstdinから渡す。quoted heredocを使うと、command内の変数やquoteをMac側shellで展開せずに送信できる。remote `resource`のmountは不要。

```sh
whub remote session handoff <PROJECT> <RUN_ID> --purpose "Rerun probe" <<'WHUB_COMMAND'
PATH="$PWD/.venv/bin:$PATH" uv run python probe.py \
  --name 'complex value'
WHUB_COMMAND
```

Linux GUI側では対象Projectの`.whub/handoff/commands.md`を開く。先頭の最新entryにはrun固有の2手順があり、Step 1のlauncher commandをGUI terminalでcopy実行して対象tmux sessionへ入り、Step 2のworkload commandをtmux内でcopy実行する。whubはMarkdown内のcommandを解析・自動実行しない。fileはProjectごとに1つで履歴を保持し、`session clean`でも削除しない。

## 状態確認

Mac側から状態とtranscriptを確認する。

```sh
whub remote session ls <PROJECT>
whub remote session show <PROJECT> <RUN_ID>
whub remote session logs <PROJECT> <RUN_ID> [--pane PANE_OR_WINDOW]
whub remote session logs <PROJECT> <RUN_ID> --follow [--pane PANE_OR_WINDOW]
```

`--follow`の切断やtmuxのdetachはremote処理を停止しない。停止は対象processへ明示し、`show`で終了code・signalと`completed`・`failed`・`interrupted`を確認する。

## 削除

`pending`または終了済みrunのdescriptor・metadata・transcriptはrun単位で削除できるが、`running` runの削除は拒否される。

```sh
whub remote session clean <PROJECT> <RUN_ID>
```
