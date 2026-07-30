# Harness research

この文書はTask 079で確認した外部知見と現行実装の事実を記録する。採用判断は含めない。

## External findings

### Git worktree

linked worktreeは、親repositoryの`$GIT_COMMON_DIR`を共有する。worktreeごとの`HEAD`とindexはprivate directoryにあるが、branch refなどは共通Git directoryにある。[git-worktree](https://git-scm.com/docs/git-worktree.html) と [gitrepository-layout](https://git-scm.com/docs/gitrepository-layout) を正本とする。

したがって、Agentへworktree directoryだけを公開し、共通Git directoryを隠す単純なfilesystem隔離では、通常のGit操作を維持できない。

### Filesystem isolation

Dockerのread-write bind mountでは、container内の変更と削除がhostへ反映される。read-only bind mountは変更と削除の両方を禁止する。[Docker bind mounts](https://docs.docker.com/engine/storage/bind-mounts/) を正本とする。

Dockerのoverlay filesystemはlower layerを消さずにwhiteoutを作るため、container内での削除はhost sourceの削除と区別できる。[OverlayFS storage driver](https://docs.docker.com/engine/storage/drivers/overlayfs-driver/) を正本とする。

### Agent runtime controls

Codex CLIのFull Autoは、sandboxedかつnetwork-disabledなcurrent directory scopeでread、write、command executionを自律実行する。[Codex CLI approval modes](https://help.openai.com/en/articles/11096431) を正本とする。

Claude Code CLIはnon-interactive modeでagentic turn数を`--max-turns`により制限でき、permission promptをMCP toolへ渡せる。[Claude Code CLI reference](https://docs.anthropic.com/en/docs/claude-code/cli-usage) を正本とする。

## Current implementation

- `NetworkPolicy`は`deny_all`だけを表現する。
- base agent authとextension agent authのnetwork grantsが異なると、`compose_auth`は拒否する。
- Codex adapterとClaude Code adapterは、command、filesystem、networkのruntime authorizationをharness必須要件として返す。生成するAgent設定だけを強制境界とは扱っていない。

## Open questions

- 削除を拒否しつつworktree内の作成・更新を許可する実行境界を、Mac上でどの方式により強制するか。
- 共通Git directoryを直接書かせずに、許可するGit操作をどの経路で実行するか。
- Agent runtime自身のprovider通信と、AgentがTaskのために行うWeb検索・package取得・git fetchを、network policyでどう分けるか。
- 自律実行の上限を、Agentic turn、wall time、token/cost、連続失敗のどれで測り、上限到達後にどの状態へ遷移させるか。
