# ADR-0014: Worktree control planeをworkspace rootに配置する

- **Status:** Accepted
- **Date:** 2026-07-29

## Context

複数のTaskを並列に実行するため、TaskごとのGit worktreeと、その親Project・branch・
workspace pathを結び付けるoperation dataが必要である。operation dataをGit worktree内に
置くとbranchごとに分岐するため、worktreeの外に単一の管理場所を定める必要がある。

同時に、既存のmanifestはProjectとResourceの正本であり、`Resource.git`はProjectが
repositoryとして管理されることを宣言している。remote Resourceのworktreeを初期から
扱う場合は、mount越しのGit操作の遅延、またはremote host側のworktreeをworkspaceへ
symlinkする仕組みを追加で扱う必要がある。

## Decision

worktree control planeはworkspace rootの`projects/worktrees/`に置く。

- 子worktreeの実体と`WorktreeDefinition` YAMLを同じdirectory直下に並べる。
- directoryとYAMLの名前は`<project>-<task-number>`、branchは
  `tasks/<task-number>`とする。`task-number`はwflowのTask ID
  `TASK-<task-number>`から取り出した数値部分である。
- `WorktreeDefinition` YAMLを先に作成し、YAMLの探索をworktree存在の正本とする。
- 親資格はmanifestの`Resource.git`で判定する。MVPはlocal Resource（`symlink`）だけを
  対象とし、remote Resourceは対象外とする。
- worktree作成はTask状態遷移と連動させず、`whub worktree`の任意操作とする。

具体的なschemaと削除安全条件は[Worktree reference](../reference/worktree.md)を正本とする。

## Rationale

- workspace root内ならエディタからworktreeと定義を一望でき、既存の`workspace_path`の
  相対パス規約をそのまま利用できる。
- definition YAMLをTask YAMLへ重複させず、definitionの探索で作成済み状態を導出できる。
- `Resource.git`を親資格に使うことで、Resourceの到達方法とrepositoryとしての役割を
  混同しない。
- remote worktreeの実装を分離し、MVPのGit操作と不整合回復を小さく保てる。

## Alternatives considered

### `~/.whub/`に配置する

configやruntimeと同じ場所に集約できるが、workspace内のprojectとして見えず、
`workspace_path`の相対パス規約も使えないため採用しない。

### Task YAMLにworktree作成済みフラグを持たせる

WorktreeDefinitionと同じ対応関係を二重に保存し、YAML先行作成や途中失敗時に不整合を
生むため採用しない。

### remote host側にworktreeを作成してmount/symlinkする

remote repositoryでも効率的に操作できるが、remote側の配置、mount、symlink、回復処理の
契約が必要になる。MVPの対象から外し、必要になった時点で別Taskとして検討する。

### `wflow`の状態遷移として作成する

worktree作成は任意の時点で行えるGit・workspace操作であり、Task状態を変更しないため
採用しない。

## Consequences

- `whub worktree`は`projects/worktrees/`を通じて定義を探索・検証する。
- directoryが存在しないdefinitionは削除せず、利用者へ不整合として表示する。
- remote Resourceのworktree対応は将来の拡張になる。
