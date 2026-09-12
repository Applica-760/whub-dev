# Architecture overview

## Domain model

`manifest.yaml` はProject、Resource、hostの単一定義源である。ResourceはProjectの配下にあり、全Resourceがworkspace上の `workspace_path` を持つ。local Resourceは `source`、remote Resourceはhostの `mount_root` からの相対 `path` で実体を表す。

workspace root自体はProjectでもResourceでもない。`WhubContext` が `~/.whub` のconfig、manifest、todo、runtime、releaseと、workspace rootの`remote_files`を一元的に扱い、consumerは保存場所を直接組み立てない。

`models/manifest.py` はI/OやContextに依存しないschemaだけを持つ。manifestの読込とworkspace rootへの束縛は`services/manifest.py`が担い、consumerは`ResolvedManifest`からworkspace path、remote host、remote pathを解決する。

## Execution boundaries

- CLI adapterは表示と引数解釈だけを担う。
- WebとCLIで共有するドメイン操作は `services` に置く。
- CLI・Webに依存しない層は `core` に置く。
- local/remoteの分岐はtargetまたはserviceへ委譲する。targetの低位エラーはserviceで `ServiceError` へ変換し、各adapterが利用者向け例外へ変換する。
- `core/remote.py` はSSH、rsync、sshfsの低位操作だけを担い、Project固有の判断を持たない。
- Agent authとCodex/Claude Code adapterの境界は[Agent adapters](agent-adapters.md)を参照する。

## Remote access

参照・編集は `whub remote mount`、実行は `whub remote run` または `whub cd` に分離する。hostごとに一つのsshfs mountを `~/.whub/runtime/mounts/` に持ち、Resourceのworkspace pathはその配下へのsymlinkとする。

mountの健全性はmount table、sshfs process、即時エラーで判断する。遅延timeoutは `slow` として正常扱いにし、timeoutを理由に自動unmountしない。

## Task Workflow

Taskの正本はGitHub Issueである。worktreeとAgent sessionはProjectとIssue番号で識別し、
状態・依存・進捗はGitHubの標準機能とIssueコメントで管理する。

archiveは読み取り専用である。Taskの依存更新、構造化ログの追記、状態遷移はactive側で解決した
Taskだけへ書き込み、参照で見つかったarchive YAMLを変更しない。

詳細な設計判断は[ADR](../ADR/)に記録する。
