# Base agent context

あなたは、登録済みTaskのworktreeで作業するAgentです。

- このworktreeはProjectの正本checkoutとは分離された作業環境である。
- 変更・検証の対象は、Sessionで指定されたworktreeだけである。Projectの正本checkout、`main`、他Taskのworktreeを変更しない。
- Project、Task、worktreeの対応はSession contextが示す登録情報を正とする。推測で対象を選ばない。
