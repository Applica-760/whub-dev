# Agent harness

登録済みTask worktreeのAgent設定とtmux sessionを扱う。

## Open

```sh
whub agent open <PROJECT> <TASK-ID> --auth <AUTH> [--auth <AUTH>]
```

OpenはauthからCodexとClaude Codeの設定をrenderし、未存在のfileだけをworktreeへ配置する。同時に、
whubが作成したfileの相対パスとhashを`projects/worktrees/agents/<project>-<task>.yaml`へ記録する。
tmux sessionがあればattachし、なければ同じTask/worktreeに新規sessionを起動する。

## Close

```sh
whub agent close <PROJECT> <TASK-ID>
```

Closeは対応tmux sessionを停止してから、Stateに記録された未変更の生成fileだけを削除する。空になった
親directoryだけを削除するため、project固有の`.claude/`や`.codex/`は残る。

所有fileの内容がOpen時のhashと異なる場合、Closeはエラーで停止する。変更内容とStateは残るため、
利用者が確認して手動で復旧または削除する。`--force`による削除は提供しない。

Close後はworktreeが残る。PR作成前にCloseを実行すると、whubが生成した未追跡設定がcommit候補へ
混入しない。tmuxがすでに終了している場合も、CloseはState cleanupを続行する。
