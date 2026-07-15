# wflow Taskロードマップビュー

## 目的・前提・方針案
- 親タスク: [Workflow YAMLによるtask-planning代替](20260713_2236_whub-task-planning-workflow-yaml.md)
- 目的: wflowのTask状態・依存関係を集計し、whub開発のロードマップをWeb appで確認できるようにする
- 方針: Markdownは長期構想と判断の記録、YAML Taskは実行事実のSSOT、Web appはwflow集計の読み取りビューとする
- 非対象: Web appからのTask状態更新・承認操作
- Task YAMLの発見方式はPhase 3の着手時に決定する

## 計画

### Phase 1: Knowledgeで責務境界を定義
- [] Workflow定義・汎用engine・Taskドメイン・Task間依存の責務とSSOTをKnowledgeへ定義する

### Phase 2: wflow運用の不足を修正
- [] accept追加・revision廃止・Phase内ログ・証跡任意化・submit_plan廃止を実装しテストする

### Phase 3: Task横断の読取機能を作成
- [] Task一覧・状態・依存関係・ブロック理由・着手可能Taskをservice/CLIで取得できるようにする

### Phase 4: Web appの読み取り専用ロードマップビューを追加
- [] Task集計APIと一覧・依存関係・進捗を表示する画面を実装し検証する

## 実行ログ

## 結果
