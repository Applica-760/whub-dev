# 目的・前提・方針案

- 目的: vault知識プレーン（inbox/daily/concepts/permanent/literature）の役割分担と昇格フローの曖昧さを解消する。分類軸を再設計し、`vault/readme.md`をSSOTに、配置判定Skillと領域マップで整理運用を回せるようにする
- 前提: ADR-0008でツール(whub)/データ(vault)のプレーンは分離済み。Obsidian廃止。`discourse` Skillが外部URL取込（→literature）を担当済み
- 前提: 今回`whub-concepts.md`は更新しない。`vault/readme.md`を知識プレーンのSSOTとする

## 確定済み意思決定（対話結果）

| # | 論点 | 決定 | 理由 |
|---|------|------|------|
| 1 | 分類軸 | **成熟度（fleeting→確立）を主軸**。起源・種別はディレクトリでなくノート内リンク/frontmatterで表現 | 軸の混在（起源/成熟度/種別/時間）が迷子の原因。1軸に寄せリンクで構造化 |
| 2 | concepts | **ディレクトリ廃止**。外部の一般概念→`literature/concept`、自分の考察→`permanent`へ移設 | 起源軸を literature(外部) / permanent(自分) の一本の境界に揃える |
| 3 | literature構成 | `log.jsonl` / `sources/`(記事・tweet) / `books/`(本) / `concept/`(一般概念)。起源＝外部で統一 | source/bookと並ぶ外部知識の一種としてconceptを新設 |
| 4 | permanent | 自分の言葉で確立した信念・洞察。フラット配置＋リンク | Zettelkasten的にフラット＋リンクで構造化 |
| 5 | daily / inbox | **両方維持**。daily＝時系列の生ログ（日記・感情可）、inbox＝トピック単位の処理待ちキュー | dailyは*いつ*、inboxは*何について*。日記の精神安定価値も残す |
| 6 | 判定Skill | **対象＝inbox内のmd**。readme+map参照で配置提案（分割含む）→承認で移動→map更新。判定不能は roadmap へ Question 化 | discourse(外部取込)と対になる内部整理Skill。dailyはスコープ外 |
| 7 | マップ | `permanent`と`literature/concept`に持たせ、**判定Skillが再生成**。手動維持しない | 静的手書きは陳腐化。Skillの重複判定・分割判断の入力にする |
| 8 | frontmatter | 各ノートに**1行summary**を持たせ、map生成と重複判定の入力にする | mapの実体は「領域内ノート一覧＋要約」 |
| 9 | vault roadmap | vault運用の方針＋**要決定の問い(Question)**を集約。現在workspace-hub roadmapに寄生中の課題を移管 | ADR-0008のプレーン分離と整合。判定不能ノートの受け皿にもなる |
| 10 | ADR/whub-concepts | 今回は起票・更新しない | readmeをSSOTとする。必要なら後続でADR-0008 Consequencesに追記 |
| 11 | literature/textbook | 分野別に体系化する知識ベースを新設。concept＝単発・横並び / textbook＝分野別に階層化・章立て | roadmapのTextbook構想の受け皿。境界を定義し再ファジー化を防ぐ |
| 12 | tasks.md | **廃止**しwhub todoへ一元化（既存タスクはaddせず破棄）。readmeはカテゴリ絵文字表のみ残す | 放置され乖離。二重管理の解消（ADR-0008の原則） |

## 未決（デフォルト提案。着手時に確定）

- Skill名: `curate`（仮）／候補 `refile`。標準Skillとの非衝突を確認
- Skill配置先: workspace-hub `.claude/skills/curate/`（discourseと同様）
- mapファイル名: 各領域直下に `_map.md`
- frontmatter summaryキー: `summary`

# 計画

## Phase 1: vault/readme.md 再設計（SSOT）
- [x] 新軸（成熟度主軸／起源・種別は従属）と昇格フロー図を記載
- [x] 5領域（daily / inbox / permanent / literature{sources,books,concept}）の役割と「どこに置くか」の判断基準を定義
- [x] frontmatter `summary` 規約・`_map.md`の位置づけ・判定Skill/discourseとの関係を記載
- [x] 旧concepts記述と `tasks.md`運用規約の扱いを整理（tasks.md統合は後続タスク据え置き）

## Phase 2: concepts廃止・移設
- [x] `literature/concept/` を新設
- [x] concepts 18件を仕分け: concept 10件 / permanent 7件 / 完璧主義は削除（価値薄）。`concepts/`削除
- [x] `literature/textbook/` を readme に位置づけ（分野別・階層・章立て。concept＝単発横並びと区別）
- [x] tasks.md 廃止（whub todoへ一元化、addなし）。readmeはカテゴリ絵文字表のみ残す
- [ ] wikilink `[[]]`→相対リンクの記法修正は別途（Phase 6で健全性のみ確認）

## Phase 3: 判定Skill `refile`
- [x] `SKILL.md`/`template.md`: inbox内md→readme+map参照→配置提案(分割含む)→承認で移動→_map更新→判定不能はroadmap Question追記
- [x] 命名確定(`refile`)、`.claude/skills/refile/`へ配置、標準Skillと非衝突

## Phase 4: 領域マップ
- [x] refileに `_map.md` 再生成機能を組込（SKILL手順5、frontmatter summary集約）
- [ ] `permanent/_map.md` と `literature/concept/_map.md` を初回生成（Phase 6のrefile実走で兼ねる）

## Phase 5: vault roadmap整備
- [x] `vault/docs/roadmap.md` 作成（方針メモ / 要決定Question）。refile初走でrecruit分担のQuestionを1件追記
- [ ] workspace-hub roadmapの「vault」セクション課題（recruit文書整理 等）を移管し、workspace-hub側は導線のみ残す

## Phase 6: 検証
- [x] refile実走（inbox/ノートをどう管理するか）でQuestion化＋inbox削除経路を確認
- [ ] permanent/concept行きノートでrefileし、振り分け・分割・`_map.md`初回生成を確認（未）
- [ ] vault/readme・各map・被参照リンクの整合を確認

# 実行ログ

# 結果
