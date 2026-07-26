# CLI reference

`whub` はMac上でworkspaceのProjectとResourceを操作するCLIである。通常の操作contextは `~/.whub` に固定する。

## ProjectとResource

```sh
whub ls
whub status
whub link
whub mount [PROJECT] [-a]
whub unmount [--force]
whub cd <PROJECT>
whub run <PROJECT> <CMD...>
```

- local Resourceはsymlink、remote Resourceはsshfs mountで参照・編集する。
- remoteの走査・長時間処理は対象host上で実行する。ワンショットは `run`、対話的作業は `cd` を使う。
- `mount` はhost単位でsshfsを1本だけ接続する。無引数では `auto_mount: true` のhostだけを対象にし、`-a` またはProject指定ではこの制限を外す。
- `unmount` はmountが作成したworkspace symlinkも撤去する。`status` の `slow` は正常系であり、`stale` と `unreadable` だけを対処対象とする。

## 作業支援

```sh
whub todo
whub backlog <TEXT> [--project PROJECT]
whub codegraph
whub get <PATH>
whub put <LOCAL_NAME>
whub shell-init [--shell zsh]
```

- `backlog` はProjectの `docs/backlog.md` に未整理メモを追記する。
- `codegraph` はmanifestで有効化したResourceだけを初期化する。
- `get` はremoteの単一fileを `~/.whub/downloads` へ取得し、`put` はその取得元へ書き戻す。

## Web appとRemote GUI session

```sh
whub app
whub app down
whub session <COMMAND>
```

Web appは読み取り用の派生ビューであり、Task YAMLは更新しない。Remote GUI sessionの予約・handoff・観測・削除は[operations/session.md](../operations/session.md)を参照する。

## Operation release

```sh
whub release build --source PATH
whub release verify RELEASE_ID
whub release apply RELEASE_ID
```

releaseの停止・復旧・検証条件は[operations/releace.md](../operations/releace.md)を正とする。
