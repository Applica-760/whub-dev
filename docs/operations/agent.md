# Agent harness

登録済みTask worktreeのAgent sessionを扱う。コマンドは[CLI reference](../reference/cli.md)、
設定生成とcleanupの契約は[Agent adapters](../architecture/agent-adapters.md)を参照する。

## Open

- 登録済みTask worktreeとauthを検証する。
- 同じTaskのtmux sessionがあれば再接続し、なければworktree sessionを作成する。
- Hub共通指示・Skills・Role・登録branchをsnapshotしてworktreeへ配置する。
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
    }]
  }
}
```

初回はnative Codex CLIで`/hooks`を開き、この定義を確認して信頼する。Hookは登録済みAgent worktreeからの
`PermissionRequest`だけを表示し、`PostToolUse`または10分のTTLで解除する。Hook実行・Web app未起動・入力の
いずれが失敗してもCodexの通常の承認promptは継続する。

診断は、Web app起動中に`whub agent attention-hook`へHook JSONをstdinで与え、`/api/agent-attention`で状態を
確認する。登録外のcwdや不正なJSONでは状態を作らない。

## Close

- tmux sessionを停止し、未変更のHarness所有設定だけを削除する。
- Project固有設定、Task、worktree、branchは変更しない。
- Harness所有設定が変更済みならcleanupを停止し、変更とStateを残す。`--force`は提供しない。
- tmux sessionが終了済みでもcleanupを続行する。
