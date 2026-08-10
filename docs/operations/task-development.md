# Task development

Taskの起票から完了までの役割分担とsession間の引継ぎを扱う。コマンドは
[CLI reference](../reference/cli.md)と[Agent harness](agent.md)を参照する。

## 役割

- ユーザー: worktree利用、計画、同期操作、merge方式を決定する。
- repo session: Task起票、親repo、worktree、Agent、PR、merge、Task完了を管理する。
- worktree session: 詳細計画、実装、検証、commitを担当する。
- Task YAMLは状態・依存、Task Markdownは目的・文脈・計画・判断・ログ、GitHubはPR・review・checks・merge結果の正本とする。

Session間では、Task YAML/Markdown pairを作業文脈、Git commitを実装結果、規約上のTask worktreeを作業対象として引き継ぐ。
会話履歴は引継ぎ対象にしない。

## 起票

- repo sessionでTaskの目的・範囲・制約を明確にする。
- ユーザーがworktreeを使うか決定する。
- 軽微Taskは親repoで実行し、worktreeとAgentのlifecycleを省略する。
- worktreeを使う場合は、親repoを同期し、`whub worktree open <PROJECT> <TTT> --auth <AUTH>`で`tasks/<TTT>`と規約pathを作成する。

## 引継ぎ

- `whub worktree open`がTask worktreeのAgent sessionを開く。
- worktree sessionはTask YAML/Markdown pairを再読込する。
- 詳細計画はTask Markdownで固めることを推奨する。Taskの性質に応じて起票時に確定してもよい。
- ユーザーが計画を承認するまで実装へ進まない。

## 実行

- worktree sessionはTask worktreeだけを変更・検証する。
- 計画・判断をTask Markdownへ記録し、進捗は`whub task log`で追記する。
- repo sessionへ戻る前にTaskを更新し、実装を検証・commitする。

## 回収と統合

- repo sessionがTask worktreeをreviewし、required checksを確認してから、`whub worktree close`の実行可否をユーザーへ確認する。承認後だけ実行する。
- `whub worktree close <PROJECT> <TTT>`がclean確認、push、PR作成または取得、merge commit、Agentとworktreeのcleanupを順に実行する。
- merge前の失敗ではAgent・worktree・branch・PRを残す。merge確認後にcleanupだけ失敗した場合も、mergeは戻さない。
- repo sessionが親repoを同期してからTaskを完了し、Task履歴をcommit・pushする。

各sessionは担当範囲の終了条件を満たしてから次へ渡す。満たさない場合はTaskを未完了のまま状態を報告する。
