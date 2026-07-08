# workflow

whub / vault / Skill をまたぐ運用ルールのSSOT。
CLIの用語・責務は `docs/whub-concepts.md`、vaultの構造と配置判断は `vault/readme.md` を正とする。

## 情報の置き場

- inbox: project非依存の思いつき・思想・外部情報・一般ナレッジの疑問を投げる場所
- todo: 実行可能な単発アクション。project紐付けは任意
- roadmap: project固有の構想・次にやりたいことを投げる場所
- task-planning: 個別作業の実行計画と作業ログ
- FOCUS.md: 次に何へ注力するかを相談するための集約ビュー

## 昇格

- inbox → todo / vault知識プレーン
- roadmap → task-planning / execution-spec / ADR
- 外部ソース → discourse → literature/log.jsonl / literature/sources
- roadmap / task-planning の開始・完了は FOCUS.md の更新材料にする

## Skill分担

- discourse: 外部ソースの取得・解説・literature記録
- refile: inbox内mdの配置提案・分割・移動
- task-planning: 実行計画と実行ログの記録
- execution-spec: 実装前に固める仕様書の作成
