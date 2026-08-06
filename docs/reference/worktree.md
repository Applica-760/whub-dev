# Worktree リファレンス

worktreeの識別と安全条件を定める。反復手順は
[worktree operation](../operations/worktree.md)、CLI契約は[CLI reference](cli.md)を参照する。

## 識別

一つのTask worktreeは、一つの親Projectと一つのTaskに属する。対応はworkspace rootの
`projects/worktrees/<project>-<task-number>.yaml`に保存する。

```yaml
schema_version: 2
task_id: TASK-072
parent_project: whub-dev
branch: tasks/072
```

- `task_id`、`parent_project`、`branch`で識別する。
- TaskとTask worktreeは一対一に対応する。
- 親Project・Taskの組、親Project内のbranch、導出したworkspace pathは重複不可とする。
- directoryとYAMLは`<project>-<task-number>`、Task branchは`tasks/<task-number>`とする。
- local配置先は`projects/worktrees/<project>-<task-number>`とする。remote配置先は
  `<mount_root>/<worktree_root>/<project>-<task-number>`から導出する。
- `worktree_root`未指定の既存manifestは`worktrees`を使う。明示値は`mount_root`相対pathに限定する。
- schema v1は、保存済み`workspace_path`が正規のlocal配置と一致する場合だけschema v2へ正規化して読む。
  新規定義はschema v2で保存し、既存定義を読込時に書き換えない。
- 定義YAMLを先に作成し、directoryがなければdiagnosticを報告する。
- 作成はTaskの状態遷移と連動しない。

## 適格性と削除

- 親repoは`git`宣言を持つlocal Resource（`symlink`）またはremote Resourceとする。
- 統合先ブランチは`resource.git.branch`とする。
- 新規Task branchは親repoの現在HEADから作成する。
- local Git操作はlocal checkout、remote Git・GitHub操作はremote host上で実行する。
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

## Remote Agent lifecycle

- Agent sessionはremote host内のworktreeでtmuxを起動し、SSHでattachする。
- Hubが配置したcontext・auth・Codex trustだけを所有stateへ記録し、close時に未変更の生成物だけを削除する。
- tmux sessionまたは生成物の確認済み不在は冪等成功とする。SSH・remote commandの失敗は不在扱いせず、
  所有stateを保持して再試行可能にする。
- 共有`~/.codex/config.toml`はremote lock内で再読込してatomicに更新する。
