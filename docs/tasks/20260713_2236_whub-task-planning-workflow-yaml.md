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
- 移植注意: remote利用を見据え、Modelと判定処理はManifest・resource解決・Mac固有path・Web・Click adapterへの依存を持たせない
- 移植条件: remote側にPython・Pydantic・PyYAMLと対象packageがあれば判定処理を実行でき、ClickはCLIを同形式で提供する場合だけ必要とする
- 配置方針: Workflow基盤を`src/whub/wflow`へまとめ、`models`・`services`・`commands`・`definitions`の層へ分ける
- CLI配置: `wflow`は`whub`とは別entry pointとし、`commands`はClick adapter、`services`はファイル操作とユースケースを担う
- 依存方向: `commands`から`services`を経て`models`を呼び、`models`はClick・whub固有path・servicesに依存しない
- 要件: ユーザーの目的・前提・方針を入力とし、Agentが情報不足・判断事項とPhase・Step形式の計画案を提示する
- 要件: ユーザー承認後だけ計画を確定し、現在状態・次に実行可能なStep・実行できない理由・必要な承認を取得できる
- 要件: 依存Task未完了・承認不足・未定義遷移を拒否し、想定外では実行を停止して理由付き計画変更を再承認する
- 要件: 未完了Step、または定義済みのTask・Phase受け入れ条件に未達があれば完了を拒否する
- 要件: 計画変更・skip・cancel・完了の理由と履歴を保持し、Taskの目的・承認済み計画・現在地・結果を追跡できる
- 分類方針: Knowledge YAMLのDefinition・Relation・Policy・Constraint・Exceptionの意味を要件整理へ転用する
- 型方針: WorkflowのState・Transitionを専用セクションで表し、条件と記録先はTransition内の`requires`・`records`に置く
- 例外方針: MVPではExceptionを設けず、skip・cancelは理由と承認を伴う明示的な状態遷移として扱う
- 雛形: 共通手順を[Workflow定義](../../src/whub/wflow/task_planning/workflow.yaml)、個別記録を[架空Task](20260713_2236_whub-task-planning-task-example.yaml)へ分離する
- ID: MVPでは参照対象のWorkflow・Task・Phase・Step・受け入れ条件だけに安定IDを付ける
- Step ID: 親Phaseの番号とPhase内連番を組み合わせた`STP-<phase>-<step>`形式を使う
- 順序: PhaseとStepは記載順に逐次実行し、前項の完了または承認付きskip後に次項へ進む
- 依存: `depends_on`はTask間の明示的な前提だけに使う任意フィールドとし、Phase・Stepには持たせない
- 受け入れ条件: 任意とし、通常はTask単位、Phaseが独立した成果物を持つ場合だけPhase単位に置き、Step単位には置かない
- 状態: Taskは`task.state`、Stepは各Step直下の`state`をSSOTとし、末尾に状態一覧を重複保持しない
- 更新: TaskはTransition時、Stepは完了またはskip時だけ近接する`state`を更新する
- 条件式: `requires`は`field`・`operator`・`value`、記録値は`$plan`・`$input`・`$actor`参照で表す
- 計画変更: 実行中から承認待ちへ戻し、変更理由と新しいplan revisionへのユーザー承認を記録する
- 計画提出: Agentは`submit_plan`で`draft`から`awaiting_approval`へ逷移し、ユーザーの`approve_plan`で実行を開始する
- デモ結果: revision 1承認後の計画変更・revision 2再承認・全Step完了・受け入れ確認・Task完了を1つの架空Taskで表現できた
- 表現可能: 計画の存在・変更理由・全Step完了・受け入れ確認・中止理由をTask Transitionの条件にできる
- 検証課題: 承認前実行・Step順序違反・現在plan revisionと承認revisionの不一致はPhase 4の検証で拒否する
- 比較結果: Step状態の可読性を維持しつつ、承認・計画変更・受け入れ結果・Task結果をMarkdownより構造化できる
- CLI配置: `wflow`を独立コマンドとし、直下はWorkflow定義、`wflow task`はtask-planning実行記録を操作する
- Checker境界: Modelは構造、checkerはWorkflowの到達可能性・終端性・trigger曖昧性を`WorkflowDiagnostic`として返す
- 命名: `$task-planning`は対話的な計画運用、`task`はYAMLで保持する実行記録とし、組込定義は`definitions/task.yaml`とする

### CLI案

| コマンド | 役割 |
|---|---|
| `wflow check [WORKFLOW]` | Workflow定義の整合性を検査する |
| `wflow graph [WORKFLOW]` | WorkflowをMermaidで出力する |
| `wflow task check TASK` | WorkflowとTaskの整合性を検査する |
| `wflow task show TASK` | 現在地・次のStep・可能な操作を表示する |
| `wflow task apply TASK TRIGGER` | 条件検証後にTask遷移と記録を更新する |
| `wflow task done TASK STEP_ID` | 次のStepを完了する |
| `wflow task skip TASK STEP_ID --reason REASON` | 理由付きで次のStepをskipする |

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
- [x] 新規デモTaskを計画承認・計画変更・再承認・検証・完了まで進行する
- [x] 拒否条件をWorkflowで表現できる範囲とPhase 4で検証すべき不足を特定する
- [x] 現行task mdと可読性・情報量・構造化範囲を比較する

### Phase 4: 検証・操作境界の確定
- [x] Workflow・Task YAMLを厳格なPydanticモデルとローダーにし、構造・ID・同一ファイル内参照を検証する
- [x] ModelをPydantic・PyYAML・標準ライブラリだけに依存させ、whub固有adapterから分離する
- [x] 雛形2ファイルの読込成功と不正構造の拒否をモデル仕様テストで証明する
- [x] Workflow・Taskモデル・service・組込定義を`src/whub/wflow` 内の層別moduleへ分離する
- [x] `wflow`を独立entry pointとし、commandsからservicesを経てmodelsへ依存する境界を確定する
- [] WorkflowとTaskをまたぐ整合性・到達不能状態・不正遷移・完了条件不足をchecker層の責務として定義する
- [x] `wflow check`・`graph`・`wflow task`の最小CLI境界を決める
- [] checker・CLI実装はモデル層の構造確定後に扱う

### Phase 5: task-planning代替判断
- [] 現行Skillとtask mdの代替条件・移行方法・既存記録の扱いを確定する
- [] 代替可能ならAgent規約・Skill・Knowledge YAMLの参照先を新方式へ切り替える
- [] backlog昇格Workflow・FOCUS派生ビュー・Task依存グラフを後続タスクへ分離する

## 実行ログ

### 試行 1: 層別移設後のテスト収集
- 実施内容: wflowと再配置したservice・webappテストを実行した
- 結果: `TaskResult`の重複class宣言により収集が失敗した
- 判断: 続行

### 試行 2: wflow層別移設と独立CLI
- 実施内容: models・services・commands・definitionsとtests/wflowへ移設し`wflow check`を追加した
- 結果: 全232テストと`wflow check`が成功した
- 判断: 続行

## 結果
