# Workflow YAMLによるtask-planning代替

## 目的・前提・方針案
- 親タスク: [whubへのYAMLグラフモデル適用案](20260713_1259_whub-graph-model-idea.md)からtask-planning代替の検討を切り出す
- 目的: 現行task-planningの手順・承認・状態遷移・記録をYAMLで構造化し、Agentが機械的に遵守できる実行基盤へ置き換える
- 最初の対象: 計画提案から承認・実行・計画変更・検証・完了までのtask-planningライフサイクルに限定する
- 後続対象: backlogからtask-planning・execution-spec・ADRなどへの昇格フローは本方式の検証後に扱う
- Workflow定義: 有効なStateと許可されるTransitionを保持し、条件と記録内容はフィールド・演算子・変数で表す
- Task実行記録: 目的・計画・Task/Step状態・承認・計画変更・中止・Task結果をWorkflow定義と分離して保持する
- SSOT: 確定した構造・現在状態・遷移規則・実行事実はYAML、背景・議論などのナラティブはMarkdownに保持する
- 導入方針: 新規デモTaskで現行Skillと比較し、代替条件を満たすまで既存task mdとSkillを廃止しない
- 前提: YAML構造と利用価値を確認するまでPydanticモデル・JSON Schema・DB・Web appを導入しない
- 要件: ユーザーの目的・前提・方針を入力とし、Agentが情報不足・判断事項とPhase・Step形式の計画案を提示する
- 要件: ユーザー承認後だけ計画を確定し、現在状態・次に実行可能なStep・実行できない理由・必要な承認を取得できる
- 要件: 依存Task未完了・承認不足・未定義遷移を拒否し、想定外では実行を停止して理由付き計画変更を再承認する
- 要件: 未完了Step、または定義済みのTask・Phase受け入れ条件に未達があれば完了を拒否する
- 要件: 計画変更・skip・cancel・完了の理由と履歴を保持し、Taskの目的・承認済み計画・現在地・結果を追跡できる
- 分類方針: Knowledge YAMLのDefinition・Relation・Policy・Constraint・Exceptionの意味を要件整理へ転用する
- 型方針: WorkflowのState・Transitionを専用セクションで表し、条件と記録先はTransition内の`requires`・`records`に置く
- 例外方針: MVPではExceptionを設けず、skip・cancelは理由と承認を伴う明示的な状態遷移として扱う
- 雛形: 共通手順を[Workflow定義](20260713_2236_whub-task-planning-workflow-template.yaml)、個別記録を[架空Task](20260713_2236_whub-task-planning-task-example.yaml)へ分離する
- ID: MVPでは参照対象のWorkflow・Task・Phase・Step・受け入れ条件だけに安定IDを付ける
- Step ID: 親Phaseの番号とPhase内連番を組み合わせた`STP-<phase>-<step>`形式を使う
- 順序: PhaseとStepは記載順に逐次実行し、前項の完了または承認付きskip後に次項へ進む
- 依存: `depends_on`はTask間の明示的な前提だけに使う任意フィールドとし、Phase・Stepには持たせない
- 受け入れ条件: 任意とし、通常はTask単位、Phaseが独立した成果物を持つ場合だけPhase単位に置き、Step単位には置かない
- 状態: Taskは`task.state`、Stepは各Step直下の`state`をSSOTとし、末尾に状態一覧を重複保持しない
- 更新: TaskはTransition時、Stepは完了またはskip時だけ近接する`state`を更新する
- 条件式: `requires`は`field`・`operator`・`value`、記録値は`$plan`・`$input`・`$actor`参照で表す
- 計画変更: 実行中から承認待ちへ戻し、変更理由と新しいplan revisionへのユーザー承認を記録する

## 計画

### Phase 1: 代替要件と責務の確定
- [x] 現行task-planningの入力・承認・実行・逸脱記録・検証・完了要件を列挙する
- [x] Workflow定義・Task実行記録・MarkdownナラティブのSSOT境界を確定する
- [x] YAMLが答える問いを「次の操作・必要な承認・遷移できない理由・完了条件」に限定する
- [x] Knowledge YAMLの分類思想を転用し、Workflowの実行概念には専用型を定義する

### Phase 2: YAML雛形の定義
- [x] Workflow定義を`schema_version`・`workflow`・`states`・`transitions`の4要素に限定する
- [x] Task実行記録の目的・Phase・Step・状態・任意の受け入れ条件・実行事実の最小フィールドを定義する
- [x] 参照対象だけの安定ID・状態遷移・計画変更の規則を定義する
- [x] Stepの状態を各Step直下へ置き、末尾の状態・結果一覧を持たない方針を決める

### Phase 3: デモTaskによる評価
- [] 新規デモTaskをYAMLで計画提案から完了まで進行する
- [] 承認前実行・依存Task未完了・証跡不足・未承認計画変更を拒否できるか確認する
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
