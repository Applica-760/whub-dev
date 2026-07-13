# whubへのYAMLグラフモデル適用案

## 目的・前提・方針案
- 目的: backlog・FOCUS・task-planningを含む長期戦略と実行管理へ、グラフの考え方を適用できるか検討する
- 背景: [AIエージェントが使う5種類のグラフ](../../vault/literature/sources/AIエージェントが使う5種類のグラフ.md)
- 課題: backlog・task-planningは役割が異なるため統合できない一方、管理箇所が散り横断アクセスしにくい
- 課題: Phase・Step・依存・優先度がテキストに留まり、見落としによる順序違反を仕組みで防げない
- 目標: Agentが用語・長期計画・現在状態・運用規約を参照し、根拠付きで次の作業を判断できるようにする
- 目標: 未完了依存の飛び越しと受け入れ条件未達の完了を、YAML検証と状態遷移コマンドで防ぐ
- 方針: グラフを論理モデルとしてYAMLで表現し、グラフDBは前提にしない
- 方針: Markdownはナラティブとして維持し、関係・状態・制約・出典だけをYAMLへ構造化する
- Knowledge YAML: [別タスク](20260713_1647_whub-knowledge-yaml.md)で用語・関係・運用規約・制約・例外を安定IDで保持する
- Task YAML: Goal・Task・Phase・Step・依存・優先度・受け入れ条件を保持する
- Workflow YAML: backlogからの昇格・承認・差し戻し・計画変更・完了などwhubの運用規則を保持する
- State YAML: Task・Phase・Stepの現在状態、検証結果、証跡、待機理由を保持する
- Execution Graph: Task YAMLの依存からNode・Edge・循環・`actionable`・未完了依存を生成し、手書きSSOTにしない
- FOCUS.md: Knowledge・Task・Workflow・StateからProjectごとの現在地を示す集約ビューとして生成する
- CodeGraph: コードから再生成できる派生インデックスとして分離し、YAMLグラフへ統合しない
- Agent利用: YAMLパスまたは安定IDを引用し、定義不一致・規約違反・依存違反・適用例外を根拠付きで示す
- 配布境界: Project内で完結するYAML照会・Task実行コマンドはAgent向け可搬CLIとして`boot`で配布する
- 配布境界: Project横断集約・resource接続・Mac固有操作はMac上のwhubだけが担う
- MVP: 4種類の入力YAML雛形とExecution Graph出力形式を定義し、新規デモデータだけで検証する
- MVP: `knowledge query`・`plan check`・`plan graph`・`plan next`・`context task`の最小コマンドを扱う
- MVP: ローカル・リモート双方のProject配下でAgent向けコマンドを利用できる構成を扱う
- MVP: Knowledge以外は現行のtask md・backlog・FOCUS・Skillを置き換えず、既存文書との自動同期とWeb appは行わない
- 状態原則: `blocked`と`actionable`を保存せず、Task自身の状態と未完了依存から導出する
- ガード: Task開始は全依存完了、Task完了は全受け入れ条件の検証と証跡記録を必須とする
- 計画変更: 実行を停止し、理由付き変更案へのユーザー承認後にYAMLを更新する
- 前提: Knowledge以外はYAML構造と利用価値を確認するまでPythonデータモデル・JSON Schema・DBを導入しない

## 計画

## Phase 1: YAMLグラフの責務決定
- [x] グラフDBを前提にせず、YAMLで論理グラフと制約を表現する方針へ変更する
- [x] Knowledge・Task・Workflow・Stateを手書き入力、Execution GraphとFOCUSを派生ビューとする
- [x] Knowledge YAMLの規約・実装・SSOT切替を[別タスク](20260713_1647_whub-knowledge-yaml.md)へ分離する
- [x] `blocked`と`actionable`を保存せず、状態と依存から導出する方針を決める
- [x] Project内コマンドを可搬CLIとして配布し、Project横断・Mac固有コマンドから分離する方針を決める
- [ ] YAMLグラフで答える問いと、各YAMLが保持する事実の境界を確定する
- [ ] YAML・Markdown・派生ビュー間で同一事実を二重管理しないSSOT規則を確定する

## Phase 2: 入出力YAML雛形
- [x] Knowledge YAMLの用語・関係・運用規約・制約・例外・安定IDを[別タスク](20260713_1647_whub-knowledge-yaml.md)で定義する
- [ ] Task YAMLへGoal・Task・Phase・Step・依存・優先度・受け入れ条件の雛形を定義する
- [ ] Workflow YAMLへ昇格・承認・差し戻し・計画変更・完了規則の雛形を定義する
- [ ] State YAMLへ現在状態・検証結果・証跡・待機理由の雛形を定義する
- [ ] Execution GraphへNode・Edge・循環・`actionable`・未完了依存の出力形式を定義する

## Phase 3: Task依存の解析と検証
- [ ] YAMLを読み込み、安定ID重複・参照切れ・許容されない依存を検出する
- [ ] Task・Phase・Stepの依存を有向グラフ化し、循環依存を検出する
- [ ] 状態と依存から`actionable`と`incomplete_dependencies`を導出する
- [ ] `plan check`・`plan graph`・`plan next`のCLI境界と出力を定義する
- [ ] Task開始と完了を依存・受け入れ条件・証跡で拒否できる状態遷移を定義する

## Phase 4: Knowledge検索とAgentコンテキスト
- [x] ID・用語・本文と直接関係を検索する`knowledge query`を[別タスク](20260713_1647_whub-knowledge-yaml.md)で実装する
- [ ] Taskに関連するKnowledge・Workflow・Stateを集約する`context task`を定義する
- [ ] Agentの着手前・計画変更前・完了前に必要なコマンドと引用形式を規約化する
- [ ] Agent向け可搬CLIとMac専用whubのコマンド境界、および`boot`配布条件を定義する
- [ ] CodeGraphのコード探索責務とYAMLコンテキスト取得責務の境界を明文化する

## Phase 5: デモ評価と次段階判断
- [ ] 新規デモProjectでBacklog整理からTask依存・次の着手対象までを表現する
- [ ] 未知語の定義参照、依存順序違反、受け入れ条件未達、計画変更承認を検証する
- [ ] Task・StateからProject別の現在地を示すFOCUSビューを生成できるか検証する
- [ ] Markdown直接参照とYAMLコマンド利用を回答精度・規約違反・参照コストで比較する
- [ ] YAMLの限界が確認された場合だけ、JSON Schema・Pythonモデル・DB・Web appを別タスクで検討する

## 実行ログ

### 試行 1: グラフDBより先に構造化YAMLで目的を検証できる
- 実施内容: Knowledge・Task・Execution・Workflow・Stateの責務と、照会・依存検証・状態遷移に必要な機能を整理した
- 結果: 4種類の入力YAMLと派生Execution Graphで、用語参照・長期計画判断・順序遵守・完了条件を検証できる見込みを得た
- 判断: 方針変更

### 試行 2: Mac専用whubへの依存ではリモートAgentがTaskを進行できない
- 実施内容: ローカル・リモートProjectでのAgent規約、CLI可用性、`boot`配布範囲を確認した
- 結果: Project内で完結するコマンドだけを可搬CLIとして配布し、Project横断操作をMacへ残す境界が必要と分かった
- 判断: 方針変更

## 結果
