# Agent adapters

Agent authの意味論は`services/agent/auth.py`が扱う。Agent固有adapterは`EffectiveAuth`を変更せず、
相対パスと内容からなるrender planを返す。Stateがplanを対象worktreeへ安全に配置し、新規作成した
fileだけをcontrol planeへ記録する。harnessはStateとtmux sessionのlifecycleを調整する。

Stateはadapterの生成物に加え、Hub rootの`AGENTS.md`と`.agents/skills`をworktreeへsnapshot投影する。
既存`AGENTS.md`と`.claude/CLAUDE.md`にはHarness所有の管理blockだけを追加し、Skillsは新規fileだけを
所有する。Stateは生成fileと管理blockのhashを一つのrecordに保存し、`close`時は未変更の所有物だけを
除去する。Hubの更新は稼働中sessionへ反映せず、close後の次回openで反映する。Harness自身はHub
contextの内容を解釈しない。

`whub agent close`はtmux sessionを停止してから、記録済みかつ内容hashが一致するfileだけを削除する。
変更済みfileは削除せずエラーにして、利用者の手動復旧を待つ。

現MVPは設定生成、tmux lifecycle、生成物cleanupまでを扱う。adapterが表現するruntime authorizationは
まだharnessで強制しておらず、filesystem・process network・Task YAML操作の強制は後続Taskの対象である。

## Codex

Codex adapterはproject-scopedな`.codex/config.toml`と`.codex/rules/whub.rules`をrenderする。
MCP serverはExtensionTool catalogの固定`command`・`args`と許可toolから構成する。

Codex rulesはargv prefixだけを表現するため、`grants.commands.exact`はrulesへ変換しない。
Codex設定はMVPの設定層であり、完全なruntime authorization boundaryではない。

Codexはtrustedなproject config layerの`.codex/rules/`を起動時に読む。rulesの詳細は
[Codex Rules](https://learn.chatgpt.com/docs/agent-configuration/rules.md)、configの詳細は
[Codex Configuration Reference](https://learn.chatgpt.com/docs/config-file/config-reference.md)を正本とする。

## Claude Code

Claude Code adapterは .claude/settings.json、PreToolUse hook、.mcp.json をrenderする。
hookはBash commandを解決済みのexact/prefix argvと照合し、登録済みExtensionToolのMCP toolだけを許可する。
パイプ・リダイレクト・command substitutionなど単一argvとして解釈できないBash構文は拒否する。

filesystemとprocess networkはhookでは完全に強制できない。harnessによるruntime guardは後続Taskで実装する。
Claude Codeのproject settings・hook・MCP仕様は
[Settings](https://code.claude.com/docs/en/settings)、
[Hooks](https://code.claude.com/docs/en/hooks)、
[MCP](https://code.claude.com/docs/en/mcp)を正本とする。
