# Agent workspace identity

## Decision

一つのTaskには、一つの子worktreeと一つのtmux sessionを対応付ける。

```text
Task 1 ── 1 worktree ── 1 tmux session
```

## Reuse

- ブラウザの切断・再接続は、対応する同一tmux sessionへ接続する。
- Agentプロセスを再起動する場合も、同一tmux session内で行う。
- Taskの目的を変更して別の作業を行う場合は、既存の対応を再利用せず、新しいTask、worktree、tmux sessionを作る。

## Consequences

- Task、worktree、tmux sessionのいずれからも、他の二つを一意に特定できる必要がある。
- worktreeの削除やtmux sessionの終了は、対応するTaskの状態と整合していなければならない。
- Agentプロセスの実行回数は、この対応関係を変更しない。
