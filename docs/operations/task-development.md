# Task development

Taskの起票から完了までの役割分担とsession間の引継ぎを扱う。コマンドは
[CLI reference](../reference/cli.md)、個別手順は[worktree operation](worktree.md)と
[Agent harness](agent.md)を参照する。

## 役割

- ユーザー: worktree利用、計画、同期操作、merge方式を決定する。
- repo session: Task起票、親repo、worktree、Agent、PR、merge、Task完了を管理する。
- worktree session: 詳細計画、実装、検証、commitを担当する。
- Task YAMLは計画・進捗・判断、GitHubはPR・review・checks・merge結果の正本とする。

Session間では、Task YAMLを作業文脈、Git commitを実装結果、worktree登録を作業対象として引き継ぐ。
会話履歴は引継ぎ対象にしない。

## 起票

- repo sessionでTaskの目的・範囲・制約を明確にする。
- ユーザーがworktreeを使うか決定する。
- 軽微Taskは親repoで実行し、worktreeとAgentのlifecycleを省略する。
- worktreeを使う場合は、親repoを同期してTask worktreeを作成する。

## 引継ぎ

- repo sessionが登録済みTask worktreeにAgent sessionを開く。
- worktree sessionはTask YAMLを再読込する。
- 詳細計画はworktree側で固めることを推奨する。Taskの性質に応じて起票時に確定してもよい。
- ユーザーが計画を承認するまで実装へ進まない。

## 実行

- worktree sessionは登録済みTask worktreeだけを変更・検証する。
- 計画・進捗・判断をTask YAMLへ記録する。
- repo sessionへ戻る前にTaskを更新し、実装を検証・commitする。

## 回収と統合

- repo sessionがAgent sessionを閉じ、Task worktreeのcleanを確認する。
- repo sessionがPRを作成し、GitHub上のreviewとrequired checksを確認する。
- ユーザーが方式を決定した後、repo sessionがmergeとcleanupを実行する。
- repo sessionが親repoを同期してからTaskを完了し、Task履歴をcommit・pushする。

各sessionは担当範囲の終了条件を満たしてから次へ渡す。満たさない場合はTaskを未完了のまま状態を報告する。
