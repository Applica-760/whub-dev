# Agent adapters

Agent authの意味論は`services/agent/auth.py`が扱う。Agent固有adapterは`EffectiveAuth`を変更せず、
設定ファイルの内容とharnessへのruntime guard要件をrender planとして返す。harnessが計画を検査し、
対象worktreeへ配置・起動・強制を担う。

## Codex

Codex adapterはproject-scopedな`.codex/config.toml`と`.codex/rules/whub.rules`をrenderする。
MCP serverはExtensionTool catalogの固定`command`・`args`と許可toolから構成する。

Codex rulesはargv prefixだけを表現するため、`grants.commands.exact`はrulesへ変換しない。
command、filesystem、networkの認可はharnessのruntime guardを必須とする。adapterはこの要件を
render planに含め、Codex設定だけを強制済みとして扱わない。

Codexはtrustedなproject config layerの`.codex/rules/`を起動時に読む。rulesの詳細は
[Codex Rules](https://learn.chatgpt.com/docs/agent-configuration/rules.md)、configの詳細は
[Codex Configuration Reference](https://learn.chatgpt.com/docs/config-file/config-reference.md)を正本とする。
