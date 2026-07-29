# Worktree operation

Taskのworktree lifecycleを扱う反復手順。worktreeの識別・PR・mergeの事実契約は
[worktree reference](../reference/worktree.md)を正本とする。

## 新規Task

1. `wflow task --project <project> init`でdraftを作成する。
2. ユーザーにworktreeを作成するか確認する。
3. 作成する場合は`whub worktree create <project> <TASK-ID>`を実行し、そのworktreeで作業する。
4. 作成しない軽微Taskは、親Projectで通常どおり作業する。

## 再開

`whub worktree check`で登録済みworktreeとdiagnosticを確認する。対象Project・Taskの
worktreeがあればそこで作業し、なければユーザーに新規作成の要否を確認する。

## 完了

worktreeなしのTaskは、全Stepの検証と通常のcommit後に`wflow task --project <project> complete`
で完了する。

登録済みworktreeのTaskは、全Stepの検証後にユーザーへPR作成を依頼する。PR作成は
`whub worktree pull-request <project> <TASK-ID>`、mergeはユーザーが指定した方式で
`whub worktree merge <project> <TASK-ID> --method <method>`を実行する。

### Project側との同期

`whub worktree pull-request`がpushするのはworktree branchだけであり、Project側の`main`に
あるcommitはpushしない。Taskの再開記録など、Project側で作られたcommitはPR作成前に
`git push origin main`で反映する。

1. Project側のTask記録をcommitし、`git push origin main`する。
2. `whub worktree pull-request <project> <TASK-ID>`でworktree branchをpushしてPRを作成する。
3. ユーザー指定の方式で`whub worktree merge <project> <TASK-ID> --method <method>`を実行する。
4. cleanup後、Project側で`git pull --ff-only`を実行する。
5. `wflow task --project <project> complete`でTaskを完了し、生成されたTask YAMLをcommit・pushする。

`git pull --ff-only`が失敗した場合は、Project側に未push commitが残っているため、merge前に
Project側のcommit/pushを完了してから同期する。
