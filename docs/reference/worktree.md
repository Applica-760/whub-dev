# Worktree リファレンス

状態: TASK-072 で実装する予定の契約。`whub worktree` は未実装。

## 目的

子 worktree は一つの manifest Project と一つの Task に属する。コードと
operation data を分離し、operation data は workspace root 配下で子 worktree
と隣接して管理する。

## 配置

```text
<workspace-root>/
  projects/worktrees/
    whub-dev-072/       # Git worktree の実体
    whub-dev-072.yaml   # WorktreeDefinition
```

`workspace_path` は引き続き workspace root からの相対パスとする。

## WorktreeDefinition

各子 worktree は一つの YAML 定義を持つ。schema は `manifest.yaml` から独立し、
親 Project と Resource の設定は引き続き manifest を正本とする。

```yaml
schema_version: 1
task_id: TASK-072
parent_project: whub-dev
branch: tasks/072
workspace_path: projects/worktrees/whub-dev-072
```

- `task_id`、`parent_project`、`branch`、`workspace_path` が一つの子 worktree を識別する。
- Task と worktree は一対一に対応する。
- Task、branch、workspace path は他の定義と重複してはならない。
- directory と YAML の名前は `<project>-<task-number>`、branch は
  `tasks/<task-number>` とする。`task-number` はwflowのTask ID
  `TASK-<task-number>`から取り出した数値部分である。
- YAML を先に作成する。YAML があって対応する directory がなければ、探索結果の
  diagnosticとして報告する。
- worktree の作成は Task の状態遷移と連動させず、任意の時点で行える。

## 親 Project の適格性

`Resource.git` は、その Project が repository であり worktree の親になれることを
示す manifest 上の宣言である。worktree 操作の前に、専用の check 関数で有効な
`git` 宣言を持たない Project を拒否する。

`symlink` と `remote` は Resource への到達方法を表すだけで、repository としての
適格性を定義しない。Git コマンドの失敗は operation failure として扱い、定義 YAML を
変更せずに報告する。

MVP は local Resource（`symlink`）だけを親にできる。remote Resource の worktree は
対象外とする。

## 削除の境界

worktree を削除する前に、tracked と untracked のいずれも変更がない clean な状態を
確認する。削除は Git worktree の実体と WorktreeDefinition YAML だけを対象とし、branch
は残す。削除が `git add`、`git commit`、`git push`、branch 削除を暗黙に実行しては
ならない。変更の公開と branch 削除は、削除とは別の明示的な操作とする。
