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
- [] Task YAMLのrevision参照を削除し、承認・変更理由・Phase完了ログを現在のplanへ簡潔に保持する
- [] Workflow定義から`submit_plan`・`awaiting_approval`を削除し、`approve_plan`を`draft`から実行開始する遷移へ更新する
- [] `wflow task accept`を追加し、受け入れ条件のpassed/failed結果と任意証跡を記録できるようにする
- [] Step完了・skip時のPhase要約と任意証跡を該当Phaseへ直接記録し、root `logs`を廃止する
- [] モデル・Task固有検証・汎用Transition適用を更新し、YAML定義をSSOTとして整合性を検査する
- [] `apply`・`done`・`skip`・`accept`のCLI契約、Task YAML例、モデル／service／CLIテストを更新する
- [] `uv run pytest`と代表的なTask CLI操作で、承認・Phase完了・受け入れ・Task完了・拒否条件を検証する

### Phase 3: Task横断の読取機能を作成
- [] Task一覧・状態・依存関係・ブロック理由・着手可能Taskをservice/CLIで取得できるようにする

### Phase 4: Web appの読み取り専用ロードマップビューを追加
- [] Task集計APIと一覧・依存関係・進捗を表示する画面を実装し検証する

## 実行ログ

### 試行 1: CON-036のYAML構文
- 実施内容: `例: Task` を含むCON-036を追加してKnowledge検証した
- 結果: YAMLのコロンが未クォート文字列として解釈され、読込に失敗した
- 判断: 文面をクォートし、内容を変えずに検証成功

## 結果
