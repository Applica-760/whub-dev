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
| 5 | 分類体系 | AI提案 + 人間承認でカテゴリ階層を育てる | 固定カテゴリは硬直、完全自動は濁る |
| 6 | MVPスコープ | **Skillのみで完結**（CLI・アプリ変更なし）。Skillはworkspace-hub側`.claude/skills/`に置く | ターミナル→whubルートでエージェント起動→即使える。摩擦最小 |
| 7 | 既存Literatureの再編 | 今回やる（7件程度、移動コスト小） | 新構造が最初からクリーンに揃う |
| 8 | 成果物 | ①ADR ②whub-concepts更新 ③intake Skill ④データrepo構築+roadmap更新 の4点 | — |
| 9 | repoの作り方 | **mind repoを転用し`vault`へ改名**（local dir・GitHub両方） | ノートのgit履歴を保持、移行作業最小 |
| 10 | repo内部構造 | 下記構造で承認（番号プレフィックス廃止、機械プレーン`whub/`同居） | Obsidian都合の番号は不要、データ一元化 |
| 11 | whubデータdir初期化 | 今回やる（`whub init <data-dir>`でworkspace側`.whub`をdata-dirへsymlink化） | manifest/todos/logの置き場を外部注入し、whub側にvault固有名を混入させない |

## 承認済み構造

```
vault/
  whub/                    # 機械プレーン: manifest.yaml, todos.yaml, literature-log.jsonl（whub initでworkspace-hub/.whubへ接続）
  inbox/                   # 旧00_inbox: 未整理の自分の思考
  literature/
    sources/               # 新設: intake③のmdノート。カテゴリ階層はAI提案+承認で育てる
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
- [ ] `whub init <data-dir>`を実装し、指定dirをworkspace-hubの`.whub/`へsymlink化（既存固定パス`.whub/manifest.yaml`・`.whub/todos.yaml`を活かす）
- [ ] `vault/whub/`へmanifest.yaml・todos.yamlを移設し、workspace-hub側でgit rm --cached＋gitignore追加（承認された場合）
- [ ] manifest.yamlのmindエントリを新repoエントリへ差し替え、`whub link`で接続確認
- [ ] readme.mdに新構造とintakeフローを記載

## Phase 3: intake Skill実装（workspace-hub側）

- [ ] `.claude/skills/intake/SKILL.md`作成: URL受領→取得（Twitterはfxtwitter/vxtwitter等ミラー経由）→翻訳・解説→verdict確認→JSONL追記、noteならmd生成（frontmatter: source/type/tags/related、本文: 和訳タイトル/要点/解説/会話で発展した問いと思考の要約）
- [ ] カテゴリ提案ロジックをSkill指示に記述（既存sources/配下を確認→分類or新設を提案→承認後に配置）

## Phase 4: 検証

- [ ] 実URLで3パターン（skip/keep/note）を通し、JSONL追記・mdノート生成・カテゴリ提案の動作を確認
- [ ] Twitterポスト（直接フェッチ不可のケース）でミラー経由取得を確認
- [ ] `whub status`/`link`/`todo`がsymlink化後も正常動作することを確認

# 実行ログ

### 試行 1: 方針転換 — mind拡張案からプライベートデータrepo案へ
- 実施内容: 貯蔵先をmind/01_Literature配下とするv2構造案を提示したところ、ユーザーから「Obsidian互換は不要」「whub＝ツール基盤、新repo＝manifest/todos/知識をすべて収める貯蔵庫」という再定義の提案
- 結果: `.whub/manifest.yaml`・`todos.yaml`がworkspace-hub repoにコミット済み（個人データ混入）であることを確認。新repo案はこの問題を構造的に解決すると評価
- 判断: 方針変更（モデルC → C'）。ブートストラップ問題は`.whub/`のsymlink化で無改修解決できる見込み

# 結果
