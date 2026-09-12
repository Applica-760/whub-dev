# Agent harness

`whub worktree open/close`が扱うIssue worktreeのAgent sessionを扱う。コマンドは[CLI reference](../reference/cli.md)、
設定生成とcleanupの契約は[Agent adapters](../architecture/agent-adapters.md)を参照する。

## Open (`whub worktree open`)

- 規約pathのIssue worktreeとauthを検証する。
- 同じIssueのtmux sessionがあれば再接続し、なければworktree sessionを作成する。
- Hub共通指示・Skills・Role・登録branchをsnapshotしてworktreeへ配置する。
- remote Resourceはhost内のworktreeへ設定をSSH経由で配置し、host内のtmux sessionを起動してSSHでattachする。Hub側はGitHub Issueを更新しない。
- 会話履歴とTask本文はOpen時のcontextへ自動注入しない。
- Hub共通指示・Skills・Roleの更新を反映する場合は、Close後にOpenし直す。

## Codex approval attention hook

Codex CLIの承認待ちをWeb appへ通知する場合だけ、利用者が`~/.codex/hooks.json`へ次を手動で追加する。
Agent openはこのuser-level設定を作成・変更しない。

```json
{
  "hooks": {
    "PermissionRequest": [{
      "hooks": [{
        "type": "command",
        "command": "~/.local/bin/whub agent attention-hook",
        "timeout": 3
      }]
    }],
    "PostToolUse": [{
      "hooks": [{
        "type": "command",
        "command": "~/.local/bin/whub agent attention-hook",
        "timeout": 3
      }]
    }],
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "~/.local/bin/whub agent attention-hook",
        "timeout": 3
      }]
    }]
  }
}
```

初回はnative Codex CLIで`/hooks`を開き、この定義を確認して信頼する。Hookは登録済みAgent worktreeからの
`PermissionRequest`と応答終了を表示する。`PostToolUse`は対応する承認待ちだけを解除し、応答終了は10分のTTLまたは
対象行の選択まで保持する。Operation TerminalからのHookは起動時に割り当てた不変`operator_id`で対象を照合するため、
表示上のOperation番号が振り直されても通知先を取り違えない。Hook実行・Web app未起動・入力のいずれが失敗してもCodexの
通常の承認promptは継続する。

診断は、Web app起動中に`whub agent attention-hook`へHook JSONをstdinで与え、`/api/agent-attention`で状態を
確認する。登録外のcwdや不正なJSONでは状態を作らない。

## Close (`whub worktree close`)

- tmux sessionを停止し、未変更のHarness所有設定だけを削除する。
- remote Resourceではtmux停止後に、Hubが所有記録したcontext・auth設定・Codex trustだけをhost上から削除する。
- Project固有設定とIssueは変更しない。worktreeとbranchの削除はmerge成功後だけ、外側のWorktree operationが行う。
- Harness所有設定が変更済みならcleanupを停止し、変更とStateを残す。`--force`は提供しない。
- tmux sessionが終了済みでもcleanupを続行する。
