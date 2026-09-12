# Task development

GitHub IssueをTaskの正本とし、計画・判断・進捗・検証はIssue本文とコメントで管理する。詳細は`issue-dev` Skillを参照する。

## 役割

- ユーザー: Issue、worktree利用、merge方式を決定する。
- repo session: Issue、親repo、worktree、Agent、PR、mergeを管理する。
- worktree session: 実装、検証、commitを担当する。

Session間ではIssue、Git commit、規約worktreeを引き継ぐ。会話履歴は引き継がない。

## Worktree

- worktreeを使う場合は`whub worktree open <PROJECT> <ISSUE-NUMBER> --auth <AUTH>`を実行する。
- `whub worktree pr <PROJECT> <ISSUE-NUMBER>`でPRを作成または取得する。
- reviewとrequired checksを確認後、ユーザー承認を得て`whub worktree close <PROJECT> <ISSUE-NUMBER>`を実行する。
- merge前の失敗ではworktree・branch・PRを残す。merge後のcleanup失敗はmergeを戻さない。
