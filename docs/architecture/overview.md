# Architecture overview

## Domain model

`manifest.yaml` はProject、Resource、hostの単一定義源である。ResourceはProjectの配下にあり、全Resourceがworkspace上の `workspace_path` を持つ。local Resourceは `source`、remote Resourceはhostの `mount_root` からの相対 `path` で実体を表す。

workspace root自体はProjectでもResourceでもない。`WhubContext` が `~/.whub` のconfig、manifest、todo、downloads、runtime、releaseを一元的に扱い、consumerは保存場所を直接組み立てない。

## Execution boundaries

- CLI adapterは表示と引数解釈だけを担う。
- WebとCLIで共有するドメイン操作は `services` に置く。
- CLI・Webに依存しない層は `core` に置く。
- local/remoteの分岐はtargetまたはserviceへ委譲する。targetの低位エラーはserviceで `ServiceError` へ変換し、各adapterが利用者向け例外へ変換する。
- `core/remote.py` はSSH、rsync、sshfsの低位操作だけを担い、Project固有の判断を持たない。

## Remote access

参照・編集は `whub remote mount`、実行は `whub remote run` または `whub cd` に分離する。hostごとに一つのsshfs mountを `~/.whub/runtime/mounts/` に持ち、Resourceのworkspace pathはその配下へのsymlinkとする。

mountの健全性はmount table、sshfs process、即時エラーで判断する。遅延timeoutは `slow` として正常扱いにし、timeoutを理由に自動unmountしない。

## Task Workflow

Taskの状態、遷移、記録形式は `src/whub/wflow/definitions/task.yaml` が正本である。保存済みTaskの整合性、操作可否、Task間関係はそれぞれ `integrity`、`eligibility`、`relation` serviceへ分離する。依存関係はTask間だけに持ち、完了またはcancelledのTaskは関係グラフに表示しない。

詳細な設計判断は[ADR](../ADR/)に記録する。
