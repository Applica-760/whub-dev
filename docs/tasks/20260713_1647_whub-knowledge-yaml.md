# whub Knowledge YAMLと検証CLI・app閲覧

## 目的・前提・方針案
- 目的: `docs/knowledge.yaml`を、確定済みの用語・関係・規約・例外・説明・背景を集約するKnowledge YAMLとして正式化する
- 親タスク: [whubへのYAMLグラフモデル適用案](20260713_1259_whub-graph-model-idea.md)からKnowledge YAMLの作成だけを切り出す
- SSOT: Knowledge YAMLに`whub-concepts.md`と`workflow.md`の全確定事項を集約し、旧MarkdownはYAMLへの薄い導線とする
- 記録範囲: 確定済みの現在の事実・規約だけを記録し、検討中の案はtask mdやbacklogに残す
- 背景: 必要になった項目だけ1行の`rationale`を追加し、詳細な比較・意思決定はADRへ昇格する
- ID: `DEF-*`・`REL-*`・`POL-*`・`EXC-*`の連番を一意に保ち、廃止後も再利用しない
- 用語境界: `whub`はMacBook上のCLI、`workspace-hub`はそのproject・repositoryとして分離する
- ADR参照: ADRと直接結び付く項目だけ任意の`ref`を持つ
- Workflow境界: 運用規約は`POL-*`として保持し、将来の実行可能なWorkflow YAMLはKnowledge IDを参照する
- 実装: Pydanticモデルと`whub knowledge check`でYAML構造・ID・参照を検証する
- 配置: 各projectの`docs/knowledge.yaml`を固定パスとし、CLIはPATHではなくTab補完可能なproject名を受け取る
- テスト方針: 方向性の変更による手戻りを避けるため、各機能の実装方針確定後にまとめて作成する
- 発展: backlogのconcept・workflow閲覧案を、YAML構築後にwhub appの専用ページとして実装する
- 非対象: Task・実行可能なWorkflow・State YAML、Execution Graph、JSON Schema、DB

## 計画

### Phase 1: Knowledge YAML規約の確定
- [x] `definitions`・`relations`・`policies`・`exceptions`の最小必須フィールドを定義する
- [x] `DEF-001`等の採番・一意性と内部参照の形式を定義する
- [x] 追加フィールドは全量移行で必要性が確認された時だけ導入する

### Phase 2: Pydanticモデルとローダー
- [x] Knowledge各要素とファイル全体のPydanticモデルを追加し、未知フィールドを拒否する
- [x] YAML構文・必須項目・ID種別・ID重複・参照切れを検証する

### Phase 3: Knowledge ServiceとCLI
- [x] `docs/whub-concept.yaml`を固定配置の`docs/knowledge.yaml`へ改名する
- [x] backlogを参考にprojectからresourceとKnowledge YAMLを解決するServiceを追加する
- [x] ID・用語・本文と直接関係を検索する最小`query`をServiceへ追加する
- [x] `whub knowledge check <project>`と`query <term> <project>`をTab補完付きで追加する
- [x] checkは件数要約、queryはAIが読めるYAMLを出力し、失敗をClick例外へ変換する

### Phase 4: 確定ナレッジの全量移行
- [x] 現行4種の既存フィールドだけを使い、任意フィールドは必要な項目に限る
- [x] 分類・記述に迷う項目は移行せず保留し、ユーザー判断を得る
- [x] Phase 4では`whub-concepts.md`と`workflow.md`を削除・縮約しない
- [x] `whub-concepts.md`の全確定事項を`DEF-*`・`REL-*`・`POL-*`・`EXC-*`へ移行する
- [x] `workflow.md`の全確定事項を主に`POL-*`として移行する
- [x] 長い意思決定はADR参照へ分離し、検討中の記述をKnowledge YAMLへ混入させない

### Phase 5: SSOT切替と検証
- [ ] 元Markdown先頭のSSOTコメントをKnowledge YAMLへ移し、参照先をKnowledgeへ切り替える
- [ ] 旧MarkdownをKnowledge YAMLへの薄い導線へ変更し、同一事実の二重管理を解消する
- [ ] 親タスクのKnowledge YAML項目を本タスクへの参照に切り替える
- [ ] `whub knowledge check`で実データを検証する

### Phase 6: whub appでの規約閲覧（詳細はPhase 5後に確定）
- [ ] backlog案を基に、whub専用ページでconcept・workflowを閲覧する要件と受け入れ基準を確定する
- [ ] 確定したAPI・UI・検証Stepを本計画へ追記して実装する

### Phase 7: テストと最終検証
- [ ] モデル・ローダー・CLI・appの正常系と主要な不正系をまとめてテストへ固定する
- [ ] `uv run pytest`とappの検証コマンドで全体回帰を確認する

## 実行ログ

## 結果
