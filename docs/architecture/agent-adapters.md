# Agent adapters

`services/agent/`は、Agent sessionの準備・終了を次の責務へ分ける。依存方向は`agent`から各サービスへ
向かい、各サービス間で相手の意味論を解釈しない。

- `agent.py`: `whub agent`が呼ぶ公開 API。登録済みworktreeを解決し、auth、context、state、sessionを順に調整する。
- `auth.py`: 権限・拡張機能・変数を解決する。Agent固有adapterは`EffectiveAuth`を変更せず、相対パスと内容からなる
  render planを返す。
- `context.py`: Hub rootの`AGENTS.md`、`.agents/skills`、baseと選択されたRoleの指示をsnapshot renderする。
- `state.py`: authのrender planとcontextを対象worktreeへ安全に具体化し、所有物を記録・cleanupする。
- `adapters/`: Agent open時に配る設定・ruleをAgent別のrender planへ純粋変換する。生成物の書込み、状態、lifecycleは所有しない。
- `adapters/codex.py`: `EffectiveAuth`をCodex project configとrulesのrender planへ変換する。
- `adapters/claude_code.py`: `EffectiveAuth`をClaude Code project settings、hook、MCP configのrender planへ変換する。
- `remote/state.py`: remote worktreeに対して、SSH経由で同じ生成物の所有・cleanup契約を実行する。remoteは汎用SSH transportと生成物の扱いだけを担い、Agent固有の意味論は持たない。
- `tmux_session.py`: tmux sessionの開始・停止だけを扱う。
- `codex/trust.py`: local/remote worktreeごとのCodex trust entryを所有・cleanupする。remote実行時もCodex trustの意味論とlockはこのserviceが持ち、SSHはtransportとしてのみ利用する。
- `codex/app_server.py`: worktreeごとのCodex App Server processとJSON-RPC状態を所有する。
- `codex/attention.py`: Codex approval requestの短期in-memory状態を保持する。
- `webapp/agent_codex_control.py`: `whub agent`からlocal web backendを起動・停止するcontrol clientであり、Codex App Server protocolは扱わない。

`state.prepare`はauthを具体化してからcontextを具体化し、両方の所有情報を一つのstate recordとして保存する。
contextはHub共通指示とRole指示を`.agents/AGENTS_context.md`へ生成し、既存`AGENTS.md`にはその参照だけを
Agent所有の管理blockとして追加する。`.claude/CLAUDE.md`はworktreeの`AGENTS.md`を参照し、Skillsは新規fileだけを
所有する。Stateは生成fileと管理blockのhashを一つのrecordに保存し、`close`時は全所有物を検証してから管理block、
生成fileの順に未変更の所有物だけを除去する。
Hubの更新は稼働中sessionへ反映せず、close後の次回openで反映する。

remote Resourceでは`agent.py`が`on_targets()`でSSH adapterを選択する。remoteの所有recordはHub側に残すため、
remote AgentはTask YAMLやHub control planeを更新しない。

## Execution context

Agent serviceがAgentへ渡す指示は、Hub共通、Role、Session固有の三層と、worktreeにもともとあるProject固有
指示から構成する。優先順は、明示的な利用者指示、Sessionの安全境界、Project固有指示、Role、Hub共通
とする。下位層は上位層の対象範囲または安全制約を緩和しない。

- Hub共通は全Projectで再利用する手順とSkillだけを扱う。Hub rootを前提にした相対パスをそのまま
  copyせず、render時にHub rootまたはworktreeのどちらを基準とするかを明示する。
- Roleは実行者の責務と許可されたTask操作を扱う。`description.md`がある選択済みextension roleだけを
  Sessionへ渡し、権限定義そのものはagent authを正本とする。
- Session固有は登録済みのProject、Task、worktreeを束縛する。implementerの変更先はこのworktreeだけであり、
  親Projectのcheckout・`main`・他Taskのworktreeを変更先にしない。未完了TaskのSSOTはHub側
  `wflow/tasks/<project>/`であり、Task YAMLの直接編集ではなく、束縛済みProject/Taskへの`wflow task`
  操作を使う。
- Project固有指示はAgent serviceが生成しない既存内容であり、管理blockの外側を変更・削除しない。

Hub contextとRole contextを含む`.agents/AGENTS_context.md`、その参照管理block、Agent serviceが新規作成した
Skill・adapter設定はAgent serviceが所有する。`close`はStateに記録した未変更の所有物だけを除去し、Project固有
指示、Agentまたは利用者が変更した内容、Task・worktree・branchは除去しない。このcontextはAgentへの説明であり、
実行時の認可境界ではない。Hookによるblock条件とlifecycle検証は別契約で定義する。

## Worktree runtime guard

Task YAMLはHubのwflow層が一元管理するため、Hub runtime hookはTask操作の場所を制限しない。worktree
runtime guardは、Agent sessionを開く際に解決した`ResolvedProjectWorktree`を唯一の実行対象とする。
branch名は再計算せず、`whub worktree create`と同じ`WorktreeDefinition.branch`を使う。定義の`tasks/<task-number>`
規則とGit worktreeの実branchの一致は既存のworktree検査で確認する。

CodexとClaude Codeへ渡すguard policyには、登録済みworktreeの絶対pathとbranchを含める。両adapterは同じ
policy rendererを使い、実行前に少なくとも次をblockする。

- session cwdまたはGit top-levelが登録済みworktreeと一致しない操作。
- 現在branchが登録済みのtask branchと一致しない操作。親Projectのcheckout、`main`、他Taskのworktreeは
  この条件で対象外となる。
- worktree外を指定するfile edit、または検証不能なshell構文による境界回避。

guardの対象外であるTask YAML操作は、中央storageを正本とする既存の`wflow task`契約に委ねる。hookは
filesystem・process全体を完全に隔離する仕組みではないため、adapterが表現できるsandbox境界と併用する。

Hub hookはAgent open/closeとbuild・verify・releaseの前提・結果を確認する。worktree hookは実行対象の
pathとbranchを検査する。両者が同じ操作を二重実行しないよう、Hubはlifecycle、worktreeは対象境界だけを
担当する。

`whub agent close`はtmux sessionを停止してから、記録済みかつ内容hashが一致するfileだけを削除する。
変更済みfileは削除せずエラーにして、利用者の手動復旧を待つ。

## Codex approval attention hook

Codexのuser-level `~/.codex/hooks.json`は、`PermissionRequest`、`PostToolUse`、`Stop`から固定の
`~/.local/bin/whub agent attention-hook`を呼ぶ。これはAgent openが生成・更新する設定ではなく、利用者が
`/hooks`で一度だけ定義を確認して信頼する任意の通知連携である。

hookはstdinのJSONから`hook_event_name`、`session_id`、`cwd`、`turn_id`、必要な場合だけ`tool_name`をcontrol planeへ
送る。`tool_input`や出力は送らない。Operation Terminalのtmux環境では起動時に生成した不変`WHUB_OPERATOR_ID`を加え、
backendは現在登録済みの`operator_id`を検証する。それ以外は、`cwd`が登録済みAgent worktreeの絶対pathと文字列として
完全一致する場合だけ、対応する`(project, task_id)`を解決する。登録外・不正な入力は状態を変更せず拒否する。

`PermissionRequest`は対象（worktreeまたはOperation）ごとの権限通知を最新の要求で置換する。`PostToolUse`は同じ
`session_id`、`tool_name`、`turn_id`を持つ権限通知だけを解除する。`Stop`は独立した応答終了通知を作るため、
PostToolUseで消えない。Codex Hookの入力にはPermissionRequestを一意に対応付ける識別子がないため、同一targetで複数の
要求が来た場合は最新の未解決要求だけを表示対象とする。各イベントは10分TTLで失効し、対象行の選択でまとめて既読化する。

hook subcommandは、stdin不正・backend未起動・通信失敗・HTTPエラーのいずれでも成功終了し、stdoutへ判断結果を
返さない。したがってHookは通常のCodex承認フローを許可・拒否・中断しない。

現MVPは設定生成、tmux lifecycle、生成物cleanupまでを扱う。adapterが表現するruntime authorizationは
まだAgent serviceで強制しておらず、filesystem・process network・Task YAML操作の強制は後続Taskの対象である。

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

filesystemとprocess networkはhookでは完全に強制できない。Agent serviceによるruntime guardは後続Taskで実装する。
Claude Codeのproject settings・hook・MCP仕様は
[Settings](https://code.claude.com/docs/en/settings)、
[Hooks](https://code.claude.com/docs/en/hooks)、
[MCP](https://code.claude.com/docs/en/mcp)を正本とする。
