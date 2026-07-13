# Workflow YAMLによるtask-planning代替

## 目的・前提・方針案
- 親タスク: [whubへのYAMLグラフモデル適用案](20260713_1259_whub-graph-model-idea.md)からtask-planning代替の検討を切り出す
- 目的: 現行task-planningの手順・承認・状態遷移・記録をYAMLで構造化し、Agentが機械的に遵守できる実行基盤へ置き換える
- 最初の対象: 計画提案から承認・実行・計画変更・検証・完了までのtask-planningライフサイクルに限定する
- 後続対象: backlogからtask-planning・execution-spec・ADRなどへの昇格フローは本方式の検証後に扱う
- Workflow定義: 許可される状態・遷移・trigger・guard・actionを保持する
- Task実行記録: 目的・計画・現在状態・実行ログ・結果・証跡をWorkflow定義と分離して保持する
- SSOT: 確定した構造・状態・遷移はYAML、背景・議論などのナラティブはMarkdownに保持する
- 導入方針: 新規デモTaskで現行Skillと比較し、代替条件を満たすまで既存task mdとSkillを廃止しない
- 前提: YAML構造と利用価値を確認するまでPydanticモデル・JSON Schema・DB・Web appを導入しない
- 要件: ユーザーの目的・前提・方針を入力とし、Agentが情報不足・判断事項とPhase・Step形式の計画案を提示する
- 要件: ユーザー承認後だけ計画を確定し、現在状態・次に実行可能なStep・実行できない理由・必要な承認を取得できる
- 要件: 依存未完了・承認不足・未定義遷移を拒否し、想定外では実行を停止して理由付き計画変更を再承認する
- 要件: StepとTaskの完了条件・検証結果・証跡を記録し、未完了Stepまたは未達条件があれば完了を拒否する
- 要件: 計画変更・skip・cancel・完了の理由と履歴を保持し、Taskの目的・承認済み計画・現在地・結果を追跡できる
- 分類方針: Knowledge YAMLのDefinition・Relation・Policy・Constraint・Exceptionの意味を要件整理へ転用する
- 型方針: Workflowの実行概念はKnowledgeのIDを流用せず、Workflow・State・Transition・Guard・Actionなどの専用型で表す
- 例外方針: MVPではExceptionを設けず、skip・cancelは理由と承認を伴う明示的な状態遷移として扱う
- 雛形: 共通手順を[Workflow定義](20260713_2236_whub-task-planning-workflow-template.yaml)、個別記録を[架空Task](20260713_2236_whub-task-planning-task-example.yaml)へ分離する
- ID: Workflow側は`WF`・`STA`・`TRN`・`GRD`・`ACT`、Task側は`TASK`・`PHA`・`STP`・`ACC`・`EVT`を使う
- 状態: Workflowの現在Stateと各Stepのstatusだけを保存し、次に実行可能なStepと未完了依存は導出する
- 計画変更: 実行中から承認待ちへ戻し、変更理由と新しいplan revisionへのユーザー承認を記録する

## 計画

### Phase 1: 代替要件と責務の確定
- [x] 現行task-planningの入力・承認・実行・逸脱記録・検証・完了要件を列挙する
- [x] Workflow定義・Task実行記録・MarkdownナラティブのSSOT境界を確定する
- [x] YAMLが答える問いを「次の操作・必要な承認・遷移できない理由・完了条件」に限定する
- [x] Knowledge YAMLの分類思想を転用し、Workflowの実行概念には専用型を定義する

### Phase 2: YAML雛形の定義
- [x] Workflow・State・Transition・Guard・Actionの最小フィールドを定義する
- [x] Task実行記録の目的・Phase・Step・状態・ログ・結果・証跡の最小フィールドを定義する
- [x] 安定ID・参照・状態導出・計画変更の規則を定義する

### Phase 3: デモTaskによる評価
- [] 新規デモTaskをYAMLで計画提案から完了まで進行する
- [] 承認前実行・未完了依存・証跡不足・未承認計画変更を拒否できるか確認する
- [] 現行task mdと比較し、欠落情報・重複管理・Agentの参照コストを評価する

### Phase 4: 検証・操作境界の確定
- [] 参照切れ・到達不能状態・不正遷移・完了条件不足の検証仕様を定義する
- [] `workflow check`・`task next`・状態遷移操作の最小CLI境界を決める
- [] 構造が確定した場合だけモデル・ローダー・CLI実装を別Phaseまたは別タスクで扱う

### Phase 5: task-planning代替判断
- [] 現行Skillとtask mdの代替条件・移行方法・既存記録の扱いを確定する
- [] 代替可能ならAgent規約・Skill・Knowledge YAMLの参照先を新方式へ切り替える
- [] backlog昇格Workflow・FOCUS派生ビュー・Task依存グラフを後続タスクへ分離する

## 実行ログ

## 結果
