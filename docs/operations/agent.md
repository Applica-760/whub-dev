# Agent harness

登録済みTask worktreeのAgent sessionを扱う。コマンドは[CLI reference](../reference/cli.md)、
設定生成とcleanupの契約は[Agent adapters](../architecture/agent-adapters.md)を参照する。

## Open

- 登録済みTask worktreeとauthを検証する。
- 同じTaskのtmux sessionがあれば再接続し、なければworktree sessionを作成する。
- Hub共通指示・Skills・Role・登録branchをsnapshotしてworktreeへ配置する。
- 会話履歴とTask本文はOpen時のcontextへ自動注入しない。
- Hub共通指示・Skills・Roleの更新を反映する場合は、Close後にOpenし直す。

## Close

- tmux sessionを停止し、未変更のHarness所有設定だけを削除する。
- Project固有設定、Task、worktree、branchは変更しない。
- Harness所有設定が変更済みならcleanupを停止し、変更とStateを残す。`--force`は提供しない。
- tmux sessionが終了済みでもcleanupを続行する。
