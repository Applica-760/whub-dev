# Documentation index

現在の設計・開発・運用の正本を短く案内する。文書の分類・配置規約はworkspace-hubの`docs/meta-documentation.md`を参照する。

## architecture

- [Architecture overview](architecture/overview.md) — ドメインモデルと主要な実行境界。
- [Agent adapters](architecture/agent-adapters.md) — Agent context、adapter、runtime guardの責務。

## reference

- [CLI reference](reference/cli.md) — `whub`の公開CLI契約。
- [Manifest reference](reference/manifest.md) — Project・Resource・hostのmanifest契約。
- [Worktree reference](reference/worktree.md) — task branch、worktree定義、PR lifecycleの契約。

## operations

- [Task development](operations/task-development.md) — Task起票からAgent作業、PR、merge、完了までのsession横断手順。
- [Agent harness](operations/agent.md) — Agent sessionのopen/closeと生成物cleanupの手順。
- [Worktree operation](operations/worktree.md) — worktreeの作成、PR、merge、cleanupの運用手順。
- [Operation release](operations/releace.md) — build、verify、applyのrelease手順と復旧条件。
- [Remote resource operation](operations/remote.md) — remote Resourceの参照・編集・実行の手順。
- [Remote GUI session](operations/session.md) — remote GUI sessionの予約・接続・観測・終了手順。

## development

- [Development conventions](development/conventions.md) — Project作業、テスト、文書化の開発規約。
- [Agent authorization](development/agent-workspace/agent-auth.md) — Agent auth、command・filesystem・network権限の契約。
- [Agent workspace control plane](development/agent-workspace/control-plane.md) — Task、worktree、sessionの管理データ境界。
- [Agent workspace identity](development/agent-workspace/identity.md) — Task、worktree、tmux sessionの一対一対応。
- [Agent workspace requirements](development/agent-workspace/requirements.md) — Agent workspaceの機能要件と優先事項。
- [Agent workspace session access](development/agent-workspace/session-access.md) — sessionへの接続とアクセス境界。
- [Agent workspace session state](development/agent-workspace/session-state.md) — session状態の意味と遷移の扱い。
- [Harness research](development/agent-workspace/harness-research.md) — harnessの調査結果と未解決事項。
- [Agent workspace known issues](development/agent-workspace/known-issues.md) — 既知の制約と未解決の問題。
- [Agent workspace task candidates](development/agent-workspace/tasks.md) — 後続Task候補の整理。

## records

- [Architecture decisions](ADR/) — 長期に残す意思決定と根拠。
- [Backlog](backlog.md) — 未着手の検討事項。
- [Specifications](specs/) — 過去の実行仕様。
- [Task history](tasks/done/) — 完了・取消Taskの凍結履歴。
