# Agent workspace identity

## Decision

一つのTaskには、一つの子worktreeと一つのtmux sessionを対応付ける。

```text
Task 1 ── 1 worktree ── 1 tmux session
```

## Reuse

- ブラウザの切断・再接続は、対応する同一tmux sessionへ接続する。
- Agentプロセスを再起動する場合も、同一tmux session内で行う。
- tmux sessionだけが失われた場合、`whub worktree open`は同じTask/worktreeのsessionを再作成する。
- `whub worktree close`はmerge成功後にsessionとwhub所有の生成設定を終了し、worktreeを削除する。
- Taskの目的を変更して別の作業を行う場合は、既存の対応を再利用せず、新しいTask、worktree、tmux sessionを作る。

## Consequences

- Task、worktree、tmux sessionのいずれからも、他の二つを一意に特定できる必要がある。
- worktreeの削除はClose後も独立した操作であり、cleanな状態でだけ許可する。
- Agentプロセスの実行回数は、この対応関係を変更しない。
