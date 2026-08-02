# Remote resource operation

remote resourceの参照・編集・実行・探索に使う手順。CLIの引数とresource契約は
[CLI reference](../reference/cli.md)を正本とする。

## Mount

- remote hostごとにsshfsを1本接続する。
- 無引数では`auto_mount: true`のhostだけを対象にする。
- Project指定または`--all`では`auto_mount: false`のhostも対象にする。

## 参照・編集・実行

- 参照・編集はmount経由で行う。
- 実行は`whub remote run <project> <command...>`または`whub cd <project>`で行う。
- mount越しの読み込みが重い単一fileは`whub remote get <project>:<path>`で取得する。編集内容をremoteへ戻す場合だけ`whub remote put <local-name>`を使う。

## 探索

- remote resourceの探索は対象Project directory以下に限定する。workspace root全体への`find`、`rg`、globはmount越しにremote tree全体を走査するため使わない。
- 横断検索・大量ファイル走査はmount上で実行せず、remote host上で`whub remote run`を使う。

```sh
whub remote run <project> grep -rn "<pattern>" <dir>
whub remote run <project> find . -name "<glob>"
whub remote run <project> codegraph explore "<symbol-or-question>"
whub remote run <project> codegraph node <symbol-or-file>
```

## 状態

`whub status`のmount列で`slow`は正常系であり対処しない。`stale`と`unreadable`だけを対処対象とする。
