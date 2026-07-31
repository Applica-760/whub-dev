# Agent workspace control plane

## Decision

Task YAML、worktree登録、Agent session、権限要求の単一情報源はoperation rootに集約する。worktreeにはコード実行に必要な内容だけを置き、branchごとにTaskやsessionの管理情報を分岐させない。

現在symlinkまたはmountで参照しているProjectを親とし、そのProjectから作成したworktreeを子として扱う。子worktreeは親Projectとの対応を保持し、whub appとCLIから識別・操作できる。

## Consequences

- 親ProjectのTask一覧とAgent運用は、どの子worktreeを開いていても一意に参照できる。
- 子worktreeの作成・再利用・削除は、親Projectのcontrol planeを通す。
- worktreeのコード変更と、Task・sessionなどのoperation dataは別の更新対象として扱う。
- Agent harnessが作成した設定の所有記録は`projects/worktrees/agents/<project>-<task>.yaml`に置く。これはworktree定義YAMLとは別で、対象worktreeのGit管理対象には含めない。
- 子worktreeをProjectとして表示・操作するための具体的なデータモデル、命名規則、CLIは後続のworktree基盤Taskで決める。
