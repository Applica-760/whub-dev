# wflow Taskロードマップビュー

## 目的・前提・方針案
- 親タスク: [Workflow YAMLによるtask-planning代替](20260713_2236_whub-task-planning-workflow-yaml.md)
- 目的: wflowのTask状態・依存関係を集計し、whub開発のロードマップをWeb appで確認できるようにする
- 方針: Markdownは長期構想と判断の記録、YAML Taskは実行事実のSSOT、Web appはwflow集計の読み取りビューとする
- 方針: Knowledge自身の定義・SSOT・記述制約も同時に整備する
- 非対象: Web appからのTask状態更新・承認操作
- Task YAMLの発見方式はPhase 3の着手時に決定する

## 計画

### Phase 1: Knowledgeで責務境界を定義
- [x] Knowledge自身の定義・SSOT・記述制約をDEF・POL・CONへ定義する
- [x] Workflow定義・汎用engine・Taskドメイン・Task間依存の責務とSSOTをKnowledgeへ定義する
- [x] DEF・POL・CONをカテゴリごとに草案提示・ユーザー承認してから反映する

### Phase 2: wflow運用の不足を修正
- [x] Task YAMLのrevision参照を削除し、承認・変更理由・Phase完了ログを現在のplanへ簡潔に保持する
- [x] Workflow定義から`submit_plan`・`awaiting_approval`を削除し、`approve_plan`を`draft`から実行開始する遷移へ更新する
- [x] `wflow task accept`を追加し、受け入れ条件のpassed/failed結果と任意証跡を記録できるようにする
- [x] Step完了・skip時のPhase要約と任意証跡を該当Phaseへ直接記録し、root `logs`を廃止する
- [x] モデル・Task固有検証・汎用Transition適用を更新し、YAML定義をSSOTとして整合性を検査する
- [x] `apply`・`done`・`skip`・`accept`のCLI契約、Task YAML例、モデル／service／CLIテストを更新する
- [x] `uv run pytest`と代表的なTask CLI操作で、承認・Phase完了・受け入れ・Task完了・拒否条件を検証する

### Phase 2.5: workflow／Task責務を分離
- [x] `services/workflow.py`へ定義の条件評価・Trigger選択・記録適用を集約し、Task非依存にする
- [x] Task serviceをTask YAMLのI/O・状態受渡し・Task固有操作と不変条件に限定する
- [x] `satisfied_if_defined`をTask固有条件評価器として注入し、engineからacceptanceの構造を除去する
- [x] 既存CLI契約を維持するmodel／service／CLIテストを更新し、`uv run pytest`で検証する

### Phase 3: Task横断の読取機能を作成
- [] Task一覧・状態・依存関係・ブロック理由・着手可能Taskをservice/CLIで取得できるようにする

### Phase 4: Web appの読み取り専用ロードマップビューを追加
- [] Task集計APIと一覧・依存関係・進捗を表示する画面を実装し検証する

## 実行ログ

### 試行 1: CON-036のYAML構文
- 実施内容: `例: Task` を含むCON-036を追加してKnowledge検証した
- 結果: YAMLのコロンが未クォート文字列として解釈され、読込に失敗した
- 判断: 文面をクォートし、内容を変えずに検証成功

### 試行 2: Task Workflow定義のレビュー
- 実施内容: CON-036・CON-038を基準にdefinitionを独立レビューした
- 結果: `complete_task`の結果要約入力だけが未宣言で、到達不能状態・曖昧Trigger・冗長定義はなかった
- 判断: `$input.result`の存在条件をdefinitionへ追加し、全243テストで検証した

### 試行 3: workflow／Task serviceの責務分離
- 実施内容: 汎用の条件評価・Trigger選択・記録適用を`services/workflow.py`へ集約し、Task固有のacceptance評価器・Task操作を`services/task.py`へ残した
- 結果: Task serviceは320行で、未使用コードよりStep順序・Phaseログ・acceptanceなどのTask固有不変条件が大半を占めた
- 判断: Step／acceptanceのDSL化は基盤を複雑にするため見送り、Phase 3でTask横断読取に必要な情報を確認してから再判断する
- 引継ぎ: Knowledgeを固定基準とし、Phase 3ではTask YAML発見方式を決定して一覧・状態・依存・ブロック理由・着手可能判定をservice/CLIへ追加する

## 結果
