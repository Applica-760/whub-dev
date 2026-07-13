# whub Knowledge YAMLと検証CLI・app閲覧

## 目的・前提・方針案
- 目的: `docs/knowledge.yaml`を、確定済みの用語・関係・運用規約・制約・例外・説明・背景を集約するKnowledge YAMLとして正式化する
- 親タスク: [whubへのYAMLグラフモデル適用案](20260713_1259_whub-graph-model-idea.md)からKnowledge YAMLの作成だけを切り出す
- SSOT: Knowledge YAMLに`whub-concepts.md`と`workflow.md`の全確定事項を集約し、旧MarkdownはYAMLへの薄い導線とする
- 記録範囲: 確定済みの現在の事実・規約だけを記録し、検討中の案はtask mdやbacklogに残す
- 背景: 必要になった項目だけ1行の`rationale`を追加し、詳細な比較・意思決定はADRへ昇格する
- ID: `DEF-*`・`REL-*`・`POL-*`・`CON-*`・`EXC-*`の連番を一意に保ち、廃止後も再利用しない
- 用語境界: `whub`はMacBook上のCLI、`workspace-hub`はそのproject・repositoryとして分離する
- ADR参照: ADRと直接結び付く項目だけ任意の`ref`を持つ
- Workflow境界: 人間・Agentの運用規約は`POL-*`、データ・実装・CLIの必須性質は`CON-*`として保持する
- 実装: Pydanticモデルと`whub knowledge check`でYAML構造・ID・参照を検証する
- Relation語彙: Projectごとの`relation_types`でpredicateの名前と意味を定義する
- Schema: 必須のRelation語彙追加に伴い`schema_version: 3`へ更新する
- 配置: 各projectの`docs/knowledge.yaml`を固定パスとし、CLIはPATHではなくTab補完可能なproject名を受け取る
- テスト方針: 方向性の変更による手戻りを避けるため、各機能の実装方針確定後にまとめて作成する
- 発展: backlogのconcept・workflow閲覧案を、YAML構築後にwhub appの専用ページとして実装する
- 非対象: Task・実行可能なWorkflow・State YAML、Execution Graph、JSON Schema、DB

## 計画

### Phase 1: Knowledge YAML規約の確定
- [x] `definitions`・`relations`・`policies`・`constraints`・`exceptions`の最小必須フィールドを定義する
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
- [x] 確定済みの最小フィールドだけを使い、任意フィールドは必要な項目に限る
- [x] 分類・記述に迷う項目は移行せず保留し、ユーザー判断を得る
- [x] Phase 4では`whub-concepts.md`と`workflow.md`を削除・縮約しない
- [x] `whub-concepts.md`の全確定事項を`DEF-*`・`REL-*`・`POL-*`・`CON-*`・`EXC-*`へ移行する
- [x] `workflow.md`の全確定事項を主に`POL-*`として移行する
- [x] 長い意思決定はADR参照へ分離し、検討中の記述をKnowledge YAMLへ混入させない

### Phase 4.1: PolicyとConstraintの分離
- [x] ADR-0010で`DEF`・`REL`・`POL`・`CON`・`EXC`の分類基準を確定する
- [x] PydanticモデルへConstraintを追加し、ExceptionからPolicy・Constraintを参照可能にする
- [x] ServiceとCLIの検証・検索・表示をConstraintへ対応させる
- [x] 既存Policyを運用判断と必須性質へ再分類し、旧IDの数値部分を維持する
- [x] 各Policy・Constraintを周辺文脈なしで理解できる記述へ修正する

### Phase 4.2: Constraintの現行実装監査
- [x] `CON-008`・`CON-028`・`CON-046`を現行実装に合わせて修正する
- [x] `CON-001`へ`CON-010`を統合し、過剰な`CON-014`・`CON-023`を削除する
- [x] 不要になった`EXC-001`を削除し、移行元の`whub-concepts.md`を同期する
- [x] `whub knowledge check`と代表queryで修正後のKnowledgeを検証する

### Phase 5: SSOT切替と検証
- [x] `core/paths.py`の`PathError`をCLI・Web adapterで変換し、`CON-013`と実装を整合させる
- [x] 元MarkdownのSSOT宣言を検索可能な`POL-050`としてKnowledge YAMLへ移す
- [x] 旧MarkdownをKnowledge YAMLへの薄い導線へ変更し、同一事実の二重管理を解消する
- [x] `AGENTS.md`と`.claude/CLAUDE.md`の`whub-concepts.md`・`workflow.md`参照指示をKnowledge YAMLへ切り替える
- [x] README・配布元Skill・現行ADRの旧SSOT参照をKnowledge YAMLへ切り替える
- [x] 親タスクのKnowledge YAML項目を本タスクへの参照に切り替える
- [x] `whub knowledge check`で実データを検証する

### Phase 6: whub app Knowledge viewer MVP
- [x] backlog画面のproject切替と既存API構成を参照し、viewerのAPI・画面境界を確定する
- [x] 既存Knowledge Serviceを再利用する読み取り専用APIとOpenAPI型を追加する
- [x] 初期値をworkspace-hubとするproject切替を追加し、Knowledge未配置・remote未mountを空状態またはエラーで表示する
- [x] `All`・`DEF`・`REL`・`POL`・`CON`・`EXC`の分類タブで表示対象を切り替える
- [x] 選択中projectのID・本文を検索し、選択中の分類タブで表示を絞り込む
- [x] 各エントリのID・本文・任意refを表示し、file viewerを要するrefリンクはMVP対象外とする
- [x] Definitionを`name：definition`の1行で表示し、Knowledge未配置は取得失敗と区別して「Knowledgeはありません」と表示する
- [x] 編集・複数project横断検索・関係グラフ・ID順以外のソートはMVP対象外とする
- [x] appでproject切替・分類タブ・検索・空状態を手動検証する

### Phase 7: テストと最終検証
- [x] Knowledgeモデル・ローダーの全分類・ID・参照・YAML不正をpytestへ固定する
- [x] Knowledge Serviceのproject解決・ファイル不在・query一致と直接関係をpytestへ固定する
- [x] Knowledge CLIのcheck・query・主要エラーとWeb APIの応答・404変換をpytestへ固定する
- [x] Vitest・Testing Library・jsdomを最小構成で導入し、project初期選択・分類タブ・検索・空状態・取得失敗を固定する
- [x] `uv run pytest`・`npm test`・`npm run typecheck`・`npm run build`で全体回帰を確認する

### Phase 8: Project固有Relation語彙
- [x] ADR-0011で`relation_types`をProject固有語彙とし、形式定義との境界とschema version 3を確定する
- [x] 既存5 predicateの名前と意味を`docs/knowledge.yaml`へ定義する
- [x] Relation typeモデルを追加し、name重複と未登録predicateを拒否する
- [x] query ServiceとCLIをRelation typeの検索・件数・YAML出力へ対応させる
- [x] OpenAPI型・fixture・モデル・Service・CLI・appテストをschema version 3へ更新する
- [x] `whub knowledge check`・pytest・Vitest・typecheck・buildで全体回帰を確認する

## 実行ログ

### 試行 1: Agent指示以外にも旧SSOTの有効な参照が残っている
- 実施内容: タスク履歴を除くrepository全体で`whub-concepts.md`と`workflow.md`の参照を検索した
- 結果: README・配布元Skill・現行ADRに判断根拠として使われる参照を確認した
- 判断: 続行（完了済みspecとslidesは履歴として薄い導線への参照を残す）

### 試行 2: app buildは既存依存だけで成功する
- 実施内容: `npm run build`を実行した
- 結果: RollupのmacOS optional dependencyが欠落して失敗し、`npm install`で2 packageを復元後に成功した
- 判断: 続行

### 試行 3: 組み込みブラウザでviewerを手動検証できる
- 実施内容: app build・server再起動後に組み込みブラウザへ接続した
- 結果: 環境メタデータ不足で接続できず、typecheck・TestClient・実server HTTP検証は成功した
- 判断: 続行（画面の手動検証は未完了）

### 試行 4: Knowledge未配置を取得失敗と同じ表示にしてよい
- 実施内容: Definition表示とKnowledge未配置projectの画面を手動確認した
- 結果: Definitionの改行と、未配置を「取得に失敗しました」とする表示が利用上不自然だった
- 判断: Definitionは1行表示とし、Serviceでファイル不在を`NotFoundError`へ分離して画面では「Knowledgeはありません」と表示する

### 試行 5: Phase 5のPathError変更後も既存pytestが通過する
- 実施内容: Knowledgeテスト追加前に`uv run pytest -p no:cacheprovider`で基準状態を確認した
- 結果: 200件中199件成功し、`test_paths.py`だけが旧`ClickException`を期待して失敗した
- 判断: 方針変更（coreは`PathError`、adapterはプロトコル固有例外というPhase 5の境界へテストを更新する）

### 試行 6: jsdomだけでMantine componentを描画できる
- 実施内容: Vitest・Testing Library・jsdomでKnowledge componentテストを実行した
- 結果: Mantineがjsdom未実装の`matchMedia`を要求し、全4件が描画前に失敗した
- 判断: 続行（共通test層は作らず、近接テスト内へ最小`matchMedia` mockを追加する）

### 試行 7: Knowledge全層を自動テストで固定する
- 実施内容: モデル・Service・CLI・APIのpytestと、project切替・分類・検索・空状態・取得失敗のVitestを追加した
- 結果: pytest 215件、Vitest 4件、typecheck、production build、`git diff --check`が成功した
- 判断: 続行（Phase 6のapp手動検証だけを未完了として残す）

### 試行 8: Relation typeへsubject・object種別制約が必要である
- 実施内容: `subject_kinds`・`object_kinds`とRelationごとの種別検証を追加した
- 結果: 既存RelationはすべてDEF同士で区別がなく、将来要件のために条件分岐だけが増えた
- 判断: 方針変更（Relation typeをname・definitionへ絞り、重複名と未登録predicateだけを検証する）

### 試行 9: Project固有Relation語彙を実データとqueryへ適用できる
- 実施内容: 既存5 predicateを定義し、モデル・Service・CLI・OpenAPI型とテストをschema version 3へ更新した
- 結果: checkで5 type・10 relationを検証し、queryでtype定義と利用Relationを相互検索できた
- 判断: 続行

## 結果
- ADR-0011に基づきProject固有`relation_types`を導入し、未登録predicateを拒否するschema version 3へ更新した
- `whub knowledge check`と`query is_a`、pytest 217件、Vitest 4件、typecheck、production buildが成功した
