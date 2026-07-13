# 目的・前提・方針案

**状態：方針確定済み（2026-07-13 ユーザ承認）**

- 目的: inbox消化に先立ち、マインド系ノートの置き場をwhub app/CLI連携を見据えて再設計する
- 前提: `vault/readme.md` が構造のSSOT。主軸＝成熟度の原則は維持する
- 前提: Obsidianリンク・`A->B`記法は旧データの名残であり尊重不要（削除可）
- 前提: whub backlogのvaultエクスプローラー・refile・`_map.md`生成は本タスクのfrontmatterスキーマを共通基盤にする
- 方針1: `permanent/` を `mind/` へ改名し、直下にノートを置かず `mind/questions/`（問い）・`mind/established/`（確立）・`mind/_map.md` で構成する
- 方針2: 分類原則「排他的で安定した軸（成熟度）＝ディレクトリ、重複し変化する軸（ジャンル）＝frontmatter」をreadmeに明文化する
- 方針3: リンク運用（`A->B`記法・wiki link）を廃止し、frontmatter `summary`（必須）+ `topics`（任意）へ置き換える
- 方針4: 昇格は常にファイル移動（inbox → mind/questions → mind/established）で統一し、refile Skill・app操作の操作系を揃える
- 方針5: `vault/recruit/` を派生文書プレーンとして新設（recruit→vault統合構想の第一歩）。志向の本体はmind、企業・選考固有の派生はrecruit（ADR-0008の境界を継承）
- 配置: PKSHA志望動機→`recruit/`、人間がAIに追いつけない・社会課題解決→`questions/`、残り18件→`established/`
- 別タスク化: recruit repoの段階移行・manifestのrecruit project扱いはvault backlogへ記録し本タスクの対象外とする
- 見送った案: mind直下フラット配置（「直下＝確立」が暗黙ルール化する）／ジャンル別ディレクトリ（複数所属・境界変動に弱い）／洗練度サブディレクトリ階層化（既決）
- 更新対象の`permanent`参照: readme.md / whub-concepts.md / refile Skill×4（.claude・.agents） / vault backlog / sourcesノート1件（done task・ADRは履歴のため対象外）
- 済: vault/.obsidian・vault/.claudian は不要のため削除済み（2026-07-13、コミット未実施）

# 計画

## Phase 1: 構造変更
- [x] `mkdir vault/mind` → `git mv vault/permanent vault/mind/established` → `vault/mind/questions/`・`vault/recruit/` 作成
- [x] questionsへ2件（人間がAIに追いつけない・社会課題解決）・recruitへ1件（PKSHA志望動機）を`git mv`で配置
- [x] 生きている参照7箇所を更新（readme.md, whub-concepts.md, refile Skill×4, vault backlog, sourcesノート）。`permanent`参照は全リポジトリでゼロを確認
- [x] recruit→vault統合の段階移行構想をvault backlogへ追記

## Phase 2: SSOT反映（vault/readme.md）
- [x] 構成図・配置表を新構造（mind/questions・mind/established・recruit・_map.md）へ更新し、昇格ルール（ファイル移動で統一）を明記
- [x] frontmatterスキーマ（`summary`必須・`topics`任意）と分類原則（成熟度＝ディレクトリ、ジャンル＝frontmatter）を規約に追記
- [x] リンク記法 `A->B` の規約を削除し「リンク運用は廃止（見つけ次第削除可）」に置換

## Phase 3: 決着の記録
- [x] `vault/docs/backlog.md` の既存Question「permanentの粒度整理」を本タスクの決着として更新

## Phase 4: ノート内容の移行（inbox消化と同時でも可）
- [x] 既存mindノートへ `summary`・`topics` を付与し、旧wiki link行を削除（全27ノート、検証で漏れゼロ）
- [x] refile Skillの配置判定を新構造（questions/establishedの2段階）へ更新
- [x] inbox 15件をrefileで振り分け（削除2・移動8・統合4・分割1。inboxは空）
- [x] `mind/_map.md` 生成（questions/established別＋topics別）・`core.md` へ自分史参照を追記
- [x] 価値観統合ノートは新設不要と決着（core.mdが既にその役割。原体験の集約先として自分史を新設）

# 実行ログ

### 試行 1: readme主要被参照の`permanent/何がしたいのか`が実在しない
- 実施内容: permanent全21ノートとreadme記載を照合
- 結果: `何がしたいのか`のみ実ファイルなし（過去に削除・改名された残骸）
- 判断: 方針変更 — readmeから削除し、統合ノート新設の検討をPhase 4へ積む

### 試行 2: inbox消化で分類不能2件が発生
- 実施内容: 構造変化AI構想（研究構想）とクレカ選び（生活の意思決定記録）の置き場をユーザと協議
- 結果: 前者はliterature/sources＋esn-lab backlogへのポインタ、後者はtextbook/finance新設＋`topics: [購入判断]`（purchase層はディレクトリでなくtopicsのビューとして実現）
- 判断: 方針変更 — textbook定義を「意思決定分析ノートも置く」に拡張してreadmeへ反映

# 結果

- vault新構造が稼働: `mind/questions`(5)・`mind/established`(22)・`recruit`(3)・`textbook/finance`新設、inboxは空
- 分類SSOTを確立: 成熟度＝ディレクトリ、ジャンル＝frontmatter `topics`。リンク運用は廃止し`summary`/`topics`がapp/CLI連携の共通データモデルとなった
- `mind/_map.md`生成、core.md・readme・refile Skill・whub-concepts更新済み。`permanent`参照は全リポジトリでゼロ
- 未コミット。後続タスク: recruit repoの段階移行（vault backlogに記録済み）
