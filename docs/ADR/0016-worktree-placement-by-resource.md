# ADR-0016: Resource種別に応じたworktree配置

- **Status:** Accepted

## Context

Task worktreeは現在、local Resourceだけを対象にし、配置先
`projects/worktrees/<project>-<task-number>`をコードで固定している。remote
Resourceにも対応するには、GitとAgentをremote host上で実行しつつ、配置先を一貫して
識別できる必要がある。

## Decision

- local Resourceのworktree配置は現行のままとし、コード内の単一定数で管理する。
- remote Resourceの配置先は`hosts.<host>.worktree_root`で定義する。値は`mount_root`からの
  相対パスとし、各Task worktreeはその配下の`<project>-<task-number>`とする。
- `WorktreeDefinition`は配置先を保持せず、Task・Project・branchから現在のmanifestとlocal定数を
  用いて都度導出する。
- remoteのcreate、check、remove、PR、mergeはresource種別で分岐し、remote host上で実行する。
- remote Agentはremote host内で起動し、SSHでattachする。Hub contextと認証生成物はclose時に
  削除する。
- Task YAMLの変更はHub側repo sessionだけが`wflow task`で行う。remote Agentからの直接更新は
  この範囲では扱わない。

## Rationale

host単位のrootは、同じhostを使う複数Resourceで設定を重複させず、mount単位の配置規約を
一つに保てる。相対パスに限定すると、worktreeがmount外へ作られることを防げる。mount rootは
変更予定がないため、実パスを定義に重複させず導出できる。remote host上でGitとAgentを動かす
ことで、sshfs経由のGit操作と対話時のレイテンシを避けられる。

## Alternatives considered

- `resource.git.worktree_root`を各Resourceに持つ: localで同一の配置先を繰り返し定義するため不採用。
- hostのrootを絶対パスにする: mount外を指定でき、remote Resourceの管理境界を越えるため不採用。
- 解決済みの実パスを`WorktreeDefinition`へ保存する: rootの変更を予定せず、配置規約を重複させるため不採用。
- sshfs mount上でGitまたはAgentを実行する: remote実行の運用契約とレイテンシ要件に反するため不採用。
- remote Agentが直接`wflow task`を更新する: Task管理の責務整理を先に要するため後続Taskへ分離。

## Consequences

manifest schema、worktree解決・定義・lifecycle、Agent harness、CLI reference、テストを更新する。
remote hostにはGit、`gh`、tmux、Agent runtimeなど、対応する操作に必要な実行環境が必要になる。
