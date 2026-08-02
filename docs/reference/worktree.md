# Worktree リファレンス

worktreeの識別と安全条件を定める。反復手順は
[worktree operation](../operations/worktree.md)、CLI契約は[CLI reference](cli.md)を参照する。

## 識別

一つのTask worktreeは、一つの親Projectと一つのTaskに属する。対応はworkspace rootの
`projects/worktrees/<project>-<task-number>.yaml`に保存する。

```yaml
schema_version: 1
task_id: TASK-072
parent_project: whub-dev
branch: tasks/072
workspace_path: projects/worktrees/whub-dev-072
```

- `task_id`、`parent_project`、`branch`、`workspace_path`で識別する。
- TaskとTask worktreeは一対一に対応する。
- 親Project・Taskの組、親Project内のbranch、workspace pathは重複不可とする。
- directoryとYAMLは`<project>-<task-number>`、Task branchは`tasks/<task-number>`とする。
- 定義YAMLを先に作成し、directoryがなければdiagnosticを報告する。
- 作成はTaskの状態遷移と連動しない。

## 適格性と削除

- 親repoは`git`宣言を持つlocal Resource（`symlink`）とする。remoteは未実装とする。
- 統合先ブランチは`resource.git.branch`とする。
- 新規Task branchは親repoの現在HEADから作成する。
- 削除前に定義とGitの整合、tracked・untrackedの変更がないことを確認する。
- 削除対象はTask worktreeと定義YAMLだけとし、Task branchは残す。
- add・commit・push・branch削除・不整合の修復は暗黙に実行しない。

## PRとmerge

- GitHub操作には`gh`を使い、cleanなTask branchをpushする。
- PRはTask branchと統合先ブランチに一致するopen PRを再利用し、なければ作成する。
- PRタイトルはTask IDとする。レビューとrequired checksはGitHubを正本とする。
- merge方式は明示必須とし、対象は一致する唯一のopen PRに限定する。
- merge時はPR取得時のhead commitとの一致を要求する。
- `MERGED`確認後だけTask worktreeと定義YAMLを削除する。
- cleanup失敗はmerge済みとして報告し、残った対象を暗黙に修復しない。
- PRのcloseとlocal・remoteのTask branch削除は暗黙に実行しない。
