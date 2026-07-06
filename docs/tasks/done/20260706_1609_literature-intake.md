# 目的・前提・方針案

- 目的: 外部リソース（英語論文・記事・Twitterポスト）を「AIに翻訳・解説させ、面白いものだけ構造化して貯蔵する」機能を作る（roadmap「Twitterからのソース取得を円滑化」「mindの位置づけ」に関連）
- ユースケース: ①解説で満足→保存不要 ②面白い→ソースだけメモし後からAI会話で引ける ③会話が発展→会話要約ごと記録
- 前提: mindはObsidian vault（00_inbox〜04_Daily）だったが、**Obsidian互換は維持しない**（根底はmdによるナレッジ管理、エディタ1つで統一する思想）
- 前提: `.whub/manifest.yaml`・`todos.yaml`はworkspace-hub repoにgit管理されており、個人データ（IP・ホスト名・todo）がコミットされている
- 方針案の争点: Skillで閉じるか / whub直下ストレージか / 独立プロジェクトか → 壁打ちの結果、whubとmind（私のデータ）の関係を先に定義することになった

# 計画

## 確定済み意思決定（壁打ち結果）

| # | 論点 | 決定 | 理由 |
|---|------|------|------|
| 1 | whub/mind統合モデル | **C': プライベートデータrepoへの統一**。whub＝ツール・機能基盤（公開可能）、新repo＝私の固有記述の貯蔵庫（manifest.yaml・todos.yaml・Literature・Permanent等をすべて収容）。whubはその入口に徹する | 「これさえ見ればいい」の正体はデータ一元化。公開可能性とデータ秘匿を構造的に両立。todo×2・inbox×2の重複解消の設計原則になる |
| 2 | Obsidian互換 | **捨てる**。プレーンmd＋相対リンク、`00_`番号や`[[]]`等のObsidian都合の構成は不要 | Obsidianは見た目の便利さに過ぎず、エディタ1つ＋AIで扱える形を優先 |
| 3 | 記録方法 | ADR起票 + whub-concepts.md更新 | 重要な設計判断のため |
| 4 | データ形式 | **JSONL全件ログ + md昇格の2層**。verdictは`skip`/`keep`/`note`の3段階。mdは`note`（会話が発展したもの）のみ作成し、会話で出た問い・自分の思考の要約を含める | ユースケース①②③に1:1対応。keepは「後からAIがJSONLをgrepして引ける」で足りる。md化のハードルが上がり貯蔵庫の質を保つ |
| 5 | 分類体系 | **`sources/`はフラット＋`tags`統制語彙**。ディレクトリ階層は作らず、JSONL静的解析の軸である`tags`に分類を寄せる。既存タグはlog内出現集合を正とし、新規は近縁確認後に承認 | クエリの軸はタグ。少数note段階でディレクトリ配置は摩擦。タグが育てば後でdir昇格でき移動も安い |
| 6 | MVPスコープ | **Skillのみで完結**（CLI・アプリ変更なし）。Skillはworkspace-hub側`.claude/skills/`に置く | ターミナル→whubルートでエージェント起動→即使える。摩擦最小 |
| 7 | 既存Literatureの再編 | 今回やる（7件程度、移動コスト小） | 新構造が最初からクリーンに揃う |
| 8 | 成果物 | ①ADR ②whub-concepts更新 ③discourse Skill ④データrepo構築+roadmap更新 の4点 | — |
| 9 | repoの作り方 | **mind repoを転用し`vault`へ改名**（local dir・GitHub両方） | ノートのgit履歴を保持、移行作業最小 |
| 10 | repo内部構造 | 下記構造で承認（番号プレフィックス廃止、機械プレーン`whub/`同居） | Obsidian都合の番号は不要、データ一元化 |
| 11 | whubデータdir初期化 | 今回やる（`whub init <data-dir>`でworkspace側`.whub`をdata-dirへsymlink化） | manifest/todos/logの置き場を外部注入し、whub側にvault固有名を混入させない |
| 12 | Skill名 | **`discourse`**（暫定`intake`から改称） | 「解説・議論を通して外部ソースを知として蓄える」ニュアンス。既知の標準Skillと非衝突（`codex`は衝突回避で除外） |
| 13 | 対象ソース | **X・ブログ・論文のみ**。本の感想は別軸で`literature/books`はスコープ外 | 取得可能な外部URLソースに限定。読書ノートは性質が異なる |
| 14 | skipのログ | **最小1行記録**（`ts/url/type/verdict`のみ、解説文は残さない） | JSONLは自動ロードされずgrepは`verdict`で絞るため汚染なし。重複検知＋閲覧履歴をほぼゼロコストで得る |
| 15 | ノート間リンク | このSkillのスコープ外。frontmatterから`related`を外す | リンク取得と議論に終始。ノート間整理は将来の別機能が担う |
| 16 | 入力単位 | 単一URL前提 | 1URLを丁寧に翻訳・議論。`whub fetch`の単ファイル前提とも整合 |

## 承認済み構造

```
vault/
  whub/                    # 機械プレーン: manifest.yaml, todos.yaml, literature-log.jsonl（whub initでworkspace-hub/.whubへ接続）
  inbox/                   # 旧00_inbox: 未整理の自分の思考
  literature/
    sources/               # 新設: discourse③のmdノート。フラット配置、分類はtags(統制語彙)が担う
    books/                 # 旧01_Literature: 読書ノート（Blog/も統合）
  concepts/                # 旧02_Concept: 一般概念
  permanent/               # 旧03_Permanent: 自分の信念
  daily/                   # 旧04_Daily
  core.md / readme.md      # tasks.mdはtodos.yamlへ統合するか要検討（後続タスク可）
```

- 補足: workspace-hub repoのgit履歴に過去のmanifest（IP等）が残るため、実公開時は履歴scrubが必要（ADRのConsequencesに記録する）
- 派生論点（今回はスコープ外、roadmapへ記録）: `permanent/PKSHA志望動機.md`等recruit由来文書の整理方針、tasks.mdとtodos.yamlの統合、mindのObsidian設定ファイル群（`.obsidian/`等）の破棄

## Phase 1: 設計判断の記録

- [x] ADR-0008「whub/データrepo分離（ツールとデータのプレーン分離）」を起票（Context/Decision/Rationale/Consequences、既存ADR形式に倣う）
- [x] whub-concepts.mdの用語定義にデータrepoの位置づけ（whubが操作する唯一の自己データストア）を追記
- [x] roadmap更新: 「Twitterソース取得円滑化」を本タスクへ紐付け、todo統合・recruit文書整理・git履歴scrubを後続タスクとして追記

## Phase 2: プライベートデータrepo構築

- [ ] repo作成（承認された方式・名前で）、旧mindノートを新構造へ移行、Obsidian残滓を整理
- [x] `whub init <data-dir>`を実装し、指定dirをworkspace-hubの`.whub/`へsymlink化（既存固定パス`.whub/manifest.yaml`・`.whub/todos.yaml`を活かす）
- [x] `vault/whub/`へmanifest.yaml・todos.yamlを移設し、workspace-hub側でgit rm --cached＋gitignore追加（承認された場合）
- [x] manifest.yamlのmindエントリを新repoエントリへ差し替え、`whub link`で接続確認
- [x] readme.mdに新構造とintakeフローを記載

## Phase 3: discourse Skill実装（workspace-hub側）

- [x] `.claude/skills/discourse/SKILL.md`作成: 単一URL受領→type判定(paper/article/tweet)→取得(tweetはfxtwitter/vxtwitter等ミラー)→日本語で和訳・要点・解説を提示→verdict確認(skip/keep/note)→`vault/whub/literature-log.jsonl`へ1行追記
- [x] JSONLスキーマ確定: `{ts,url,type,title,verdict,summary,tags,note}`。skipは`ts/url/type/verdict`のみの最小行、keepはsummary/tags厚め、noteはnoteパス付き
- [x] noteフロー: `vault/literature/sources/`へフラット生成、分類はtags統制語彙が担う
- [x] `template.md`作成: JSONLスキーマ＋mdノート雛形（frontmatter: source/type/tags/date、本文: 和訳タイトル/要点/解説/議論で発展した問いと考え）＋種タグ語彙(llm,agent,rl,systems,productivity,career)

## Phase 4: 検証

- [x] note経路を実URL（Courrier→Atlantic再構成）で通し、JSONL追記(妥当性検証済)・mdノート生成・新タグ`society`承認を確認。skip/keepは構造的にnoteの部分集合
- [x] Xポスト（tweet）を`api.fxtwitter.com`経由で取得確認。本文＋引用元ツイートまで取得成功
- [x] `whub status`でsymlink化後もvault=ok（git差分2件）を確認

# 実行ログ

### 試行 1: 方針転換 — mind拡張案からプライベートデータrepo案へ
- 実施内容: 貯蔵先をmind/01_Literature配下とするv2構造案を提示したところ、ユーザーから「Obsidian互換は不要」「whub＝ツール基盤、新repo＝manifest/todos/知識をすべて収める貯蔵庫」という再定義の提案
- 結果: `.whub/manifest.yaml`・`todos.yaml`がworkspace-hub repoにコミット済み（個人データ混入）であることを確認。新repo案はこの問題を構造的に解決すると評価
- 判断: 方針変更（モデルC → C'）。ブートストラップ問題は`.whub/`のsymlink化で無改修解決できる見込み

### 試行 2: `whub init`でdata-dirを外部注入する
- 実施内容: `whub init <data-dir>`を追加し、`.whub`を`vault/whub`へのsymlinkとして作成。manifest/todos/downloadsを`vault/whub/`へ移設
- 結果: `whub init`初回・再実行skip・`whub status`・`whub todo`が成功。再実行時の自己参照チェック順序バグは修正済み
- 判断: 続行

### 試行 3: vaultを承認済み構造へ整理
- 実施内容: `00_inbox`等の番号付きディレクトリを`inbox`/`literature`/`concepts`/`permanent`/`daily`へ移動し、`literature/sources`を新設
- 結果: 旧LiteratureのBlogノートも`literature/books`直下へ統合し、`vault/readme.md`を新構造に更新
- 判断: 続行

### 試行 4: vaultをAgent配布対象から外す
- 実施内容: vaultはprivate data storeとして扱うためmanifestの`boot`をfalseにし、vault内のAgent関連ファイルを削除
- 結果: `.obsidian`・`.claudian`は残し、`whub status`でvaultのsymlink状態が正常であることを確認
- 判断: 続行

### 試行 5: Skill設計と命名の確定（壁打ち）
- 実施内容: intake Skillのフロー・データ形式・命名を検討。命名は「解説・議論を通して知として蓄える」ニュアンスで再選定し`discourse`に決定（`codex`はCodex CLIと衝突で除外）
- 結果: 対象=X/ブログ/論文のみ（本は別軸）、入力=単一URL、skip=最小1行ログ、ノート間リンクはスコープ外（frontmatterの`related`削除）を確定。Phase 3を詳細化
- 判断: 続行（Phase 3実装へ）

### 試行 6: 分類方式をフラット＋タグへ緩和し、Skill実ファイル作成
- 実施内容: whub統合の壁打ちで「JSONL書き込み=Skill/読み取り=CLI後付け」の3層分離を整理。分類はディレクトリ階層をやめ`sources/`フラット＋`tags`統制語彙に緩和（決定#5/#10更新）。`SKILL.md`・`template.md`を作成
- 結果: 種タグからHCI/philosophyを除外しllm/agent/rl/systems/productivity/careerを採用。Skillがロード可能なことを確認
- 判断: 続行（Phase 4検証へ）

### 試行 7: 実URL（Courrier→Atlantic）でnote経路を検証
- 実施内容: `courrier.jp`・`theatlantic.com`ともWebFetch不可。二次ソース＋WebSearchでBrooks『How America Got Mean』の主張を再構成し、note昇格まで通した
- 結果: JSONL初回作成+1行追記(python検証で妥当)、mdノート生成、種語彙外の新タグ`society`承認まで動作。改善点2件→①間接Fetchをtweet専用から「直接不可なら二次ソース再構成」へ一般化（SKILL.md反映済）②種タグが技術偏重で人文系に不足→提案フローが機能することを確認
- 判断: note経路は完了。tweet経路は未検証（URL未入手）

### 試行 8: tweet取得検証＋JSONL置き場の再検討（未決）
- 実施内容: tweetを`api.fxtwitter.com`経由で取得（本文＋引用元ツイートまで成功）。あわせてlog置き場`vault/whub/`（ADR-0008で機械プレーンの「各種ログ」）の妥当性を再検討
- 結果: manifest/todosは全project横断のwhub基盤だが、literature-logは単一ドメインのコンテンツ索引で非対称。`literature/log.jsonl`への移設が凝集の観点で優位。ただし「全ドメイン横断で一括grep」を重視するならwhub/中央集約も一理（トレードオフ）
- 判断: 未決（要ユーザー決定）。移設する場合SKILL.md/template.mdのパスとADR-0008に反映。現在1エントリのため移動コスト小

### 試行 9: logをliteratureへ移設＋tweetをkeep記録
- 実施内容: ユーザー決定によりlogを`vault/whub/literature-log.jsonl`→`vault/literature/log.jsonl`へ移設。tweet(@_kohta)をkeepで記録。SKILL.md/template.md/ADR-0008のパスと機械プレーン定義を更新
- 結果: log 2行(note+keep)で妥当性検証OK。ADR-0008に「機械プレーンは全project横断のwhub基盤に限り、単一ドメイン索引は知識ドメイン配下」を明文化。新タグ`software-engineering`/`ai`が語彙に加わる
- 判断: Phase 3/4完了。skip経路のみ実データ汚染回避で未実施（note/keepの部分集合）

# 結果
