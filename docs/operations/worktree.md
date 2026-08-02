# Worktree operation

Taskのworktree lifecycleを扱う。コマンドは[CLI reference](../reference/cli.md)、
識別・PR・mergeの事実契約は[worktree reference](../reference/worktree.md)を正本とする。

## 作成

- 作成前に親repoで統合先ブランチをcheckoutし、`git status --short --branch`を確認する。
- cleanかつremoteと同期済みなら作成へ進む。
- aheadなら、PR差分への混入を防ぐためpushが必要なことを説明し、ユーザーの承認後にpushする。
- behindなら、ユーザーの承認後に`git pull --ff-only`を実行する。
- dirtyまたはdivergedなら作成せず、状態を報告する。
- 同期後にTask worktreeを作成する。

## 再開

- worktree checkで登録とdiagnosticを確認する。
- 対象のTask worktreeがあればそこで作業する。
- 登録がなければユーザーに作成の要否を確認する。

## 統合

- PR作成前にTask worktreeをcleanにする。
- Task branchをpushしてPRを作成する。
- 通常は、検証済みcommitを保持する`merge`を選ぶ。
- `squash`は試行錯誤のcommitをまとめる場合、`rebase`はcommit SHAの変更を許容する場合だけ選ぶ。
- 成功時はTask worktreeと定義YAMLが削除されたことを確認する。Task branchは削除されない。
- merge失敗時はTask worktreeを保持する。
- merge成功後のcleanup失敗時はmergeを再実行せず、残存状態を報告する。

## 親repo同期

- merge後に親repoで`git pull --ff-only`を実行する。
- 失敗時は分岐を解決するまで次へ進まない。
