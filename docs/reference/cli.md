# CLI reference

`whub` はMac上でworkspaceのProjectとResourceを操作するCLIである。通常の操作contextは `~/.whub` に固定する。

## ProjectとResource

```sh
whub ls
whub status
whub link
whub remote mount [PROJECT] [-a]
whub remote unmount [--force]
whub cd <PROJECT>
whub remote run <PROJECT> <CMD...>
whub remote cleanup-appledouble <PROJECT> [--apply]
```

- local Resourceはsymlink、remote Resourceはsshfs mountで参照・編集する。
- remoteの走査・長時間処理は対象host上で実行する。ワンショットは `remote run`、対話的作業は `cd` を使う。
- `remote cleanup-appledouble` はremote host上でAppleDouble sidecarを検証して一覧表示し、`--apply`指定時だけ削除する。SSHFS mountは走査しない。
- `remote mount` はhost単位でsshfsを1本だけ接続する。無引数では `auto_mount: true` のhostだけを対象にし、`-a` またはProject指定ではこの制限を外す。
- `remote unmount` はmountが作成したworkspace symlinkも撤去する。`status` の `slow` は正常系であり、`stale` と `unreadable` だけを対処対象とする。
- `status` はResource状態に加えて登録済みworktreeを診断する。正常時は登録数と`ok`を表示し、worktree diagnosticがあれば対象と理由を表示して非0で終了する。worktreeの詳細一覧は `worktree check` を使う。

## Worktree

```sh
whub worktree create <PROJECT> <TASK-ID>
whub worktree check
whub worktree remove <PROJECT> <TASK-ID>
```

- `create` は、親Projectとその`docs/tasks/`に存在するTask YAMLからbranch・workspace pathを導出して登録・作成する。同じProject・Taskの登録は上書きせず拒否する。成功時は親Project、Task、branch、workspace pathを表示し、失敗時は非0で終了する。
- `check` は、すべての登録済みworktreeを親Project、Task、branch、workspace path、diagnosticとともに表示する。Git・YAMLは変更せず、diagnosticが一つでもあれば非0で終了する。
- `remove` は親Project・Taskで一つの登録を選択し、cleanかつ整合したGit worktreeだけを削除する。Git worktreeと定義YAMLのみを削除し、branchは残す。`--force`、commit・push・branch削除、不整合の自動修復は行わない。
- remote Resourceを親にするworktreeは未実装であり、明示的にエラーとなる。

## 作業支援

```sh
whub todo
whub backlog <TEXT> [--project PROJECT]
whub codegraph
whub remote get <PATH>
whub remote put <LOCAL_NAME>
whub remote rm <LOCAL_NAME>
whub shell-init [--shell zsh]
```

- `backlog` はProjectの `docs/backlog.md` に未整理メモを追記する。
- `codegraph` はmanifestで有効化したResourceだけを初期化する。
- `remote get` はremoteの単一fileをworkspace rootの `remote_files/` へ取得し、`remote put` はその取得元へ書き戻す。
- `remote rm` は管理済みの `remote_files/` 配下fileと対応メタデータを削除する。`whub remote get` で取得していないfileは削除しない。

## Web appとRemote GUI session

```sh
whub app
whub app down
whub remote session <COMMAND>
```

Web appは読み取り用の派生ビューであり、Task YAMLは更新しない。Remote GUI sessionの予約・handoff・観測・削除は[operations/session.md](../operations/session.md)を参照する。

`/worktrees` は `GET /api/worktrees` を用いる読み取り専用一覧である。親Project、Task、branch、workspace path、diagnosticを表示し、作成・削除・session操作は提供しない。

## Operation release

```sh
whub release build --source PATH
whub release verify RELEASE_ID
whub release apply RELEASE_ID
```

releaseの停止・復旧・検証条件は[operations/releace.md](../operations/releace.md)を正とする。
