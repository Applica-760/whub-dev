# Worktree リファレンス

状態: TASK-074で実装済みの契約。PR/merge lifecycleはTASK-081で実装予定。

## 目的

子 worktree は一つの親Projectと一つのTaskに属する。コードと
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
- 親ProjectとTaskの組、同一親Project内のbranch、workspace pathは他の定義と重複してはならない。
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

MVP は local Resource（`symlink`）だけを親にできる。remote Resource を指定すると、未実装であることを示すエラーを返す。

## 削除の境界

worktree を削除する前に、tracked と untracked のいずれも変更がない clean な状態を
確認する。削除は Git worktree の実体と WorktreeDefinition YAML だけを対象とし、branch
は残す。削除が `git add`、`git commit`、`git push`、branch 削除を暗黙に実行しては
ならない。変更の公開と branch 削除は、削除とは別の明示的な操作とする。

## PR と merge lifecycle

PR と merge はGitHub専用操作とし、GitHub CLI `gh`を利用する。対象は既存の
`parent_project` と `task_id` の組で特定する。PR作成時はtask branchをpushし、
`manifest.git.branch` を統合先にする。PRのタイトルは `TASK-ID` とし、作業内容は
対象Task YAMLを正本とする。

merge方式は明示必須とする。レビュー承認、branch protection、required checksは
GitHubを正本とし、CLIは承認を記録・代行しない。GitHubでmergeが成功した場合だけ、
既存の安全なremove操作でcleanなworktreeと定義YAMLを削除する。mergeまたはcleanupが
失敗した場合は、対象を削除しない。PR操作とcleanupはいずれもtask branchを削除しない。

## Status と Web app

実行時の状態は `StatusReport` が表す。正常な worktree は親Resourceの
`ResourceStatus.worktrees` に属し、親Projectを確定できない不正な定義だけが
`StatusReport.invalid_worktrees` に残る。定義 YAML は引き続き
`parent_project` で親を参照するだけで、manifest Resourceを複製しない。

`whub status` はResource表を維持したままworktree診断を総合する。登録済み件数と
正常・異常を表示し、worktree diagnosticが一つでもあれば非0で終了する。詳細な
一覧・診断は `whub worktree check` が担当する。

Web appの `GET /api/worktrees` と `/worktrees` は、親Project、Task、branch、
workspace path、diagnosticを読み取り専用で表示する。作成・削除・Task状態遷移・
Agent sessionの起動、再接続、対応保存は扱わない。
