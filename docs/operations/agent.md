# Agent harness

登録済みTask worktreeのAgent設定とtmux sessionを扱う。

## Open

```sh
whub agent open <PROJECT> <TASK-ID> --auth <AUTH> [--auth <AUTH>]
```

OpenはauthからCodexとClaude Codeの設定をrenderし、未存在のfileだけをworktreeへ配置する。同時に、
whubが作成したfileの相対パスとhashを`projects/worktrees/agents/<project>-<task>.yaml`へ記録する。
tmux sessionがあればattachし、なければ同じTask/worktreeに新規sessionを起動する。

Open時にはHub rootの`AGENTS.md`もworktreeの`AGENTS.md`へ管理blockとしてsnapshot配置し、Hubの
`.agents/skills`をworktreeへコピーする。Claude Codeはworktreeの`.claude/CLAUDE.md`から同じ
`AGENTS.md`を参照する。Hubの相対パスは管理block内に記録されるHub rootを基準に解決する。
Hubを更新した後は、対象sessionをCloseしてからOpenし直す。

## Close

```sh
whub agent close <PROJECT> <TASK-ID>
```

Closeは対応tmux sessionを停止してから、Stateに記録された未変更の生成fileだけを削除する。空になった
親directoryだけを削除するため、project固有の`.claude/`や`.codex/`は残る。

管理blockの外側に加えたproject側・利用者側の編集は残す。管理block自体またはHarness所有Skillを変更
した場合、Closeは安全のためエラーで停止する。

所有fileの内容がOpen時のhashと異なる場合、Closeはエラーで停止する。変更内容とStateは残るため、
利用者が確認して手動で復旧または削除する。`--force`による削除は提供しない。

Close後はworktreeが残る。PR作成前にCloseを実行すると、whubが生成した未追跡設定がcommit候補へ
混入しない。tmuxがすでに終了している場合も、CloseはState cleanupを続行する。
