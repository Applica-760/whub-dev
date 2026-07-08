# 文脈外部化トラックの設計整理（状態文書・投入口Webアプリ・語彙再設計）

## 目的・前提・方針案
- 目的: 「次に何をするか」の判断材料を外部化する一連の構想（旧称STATUS.md・投入口Webアプリ・projectごとのindex）を1つの設計トラックとして整理し、実装可能な状態まで固める
- 前提（壁打ち2ラウンドで確定済み）:
    - SSOTは二層: 個人横断（inbox・todo・マインド系・状態文書）はvault、プロジェクト固有（roadmap）は各プロジェクトリソース内
    - 状態文書はwhub側が持つ「各projectの代表的な状態」の集約で、mount/link不要で参照できる。各roadmapはより細粒度で、必要時・作業中のみ参照
    - 状態文書の用途は「Agentに次に着手すべきことを相談する」機能の材料。推薦＋理由＋タイムボックス提示、人間は承認/拒否のみ
    - 更新・相談はSkill起動で行う（whubコマンドは噛ませない）。ただしSkill作成は概念・命名確定後
    - backlogやcaptureという中間段は導入しない。project非依存はinbox、project固有はroadmapへ直接投げる
    - Web appはstatus/todo/roadmap/状態文書を統合表示するフロントエンド。md/jsonlがソース、HTMLはビュー。手動`whub app`起動、スマホはtailscale＋ブラウザ
    - Node系依存は許容。超長期的にはwhubをWeb/Pythonコンポーネントの共通化・エクスポート基盤にする（boot方式の拡張。portfolio等が逆にwhubへ依存する形も許容）
- 方針: 概念・語彙 → 文書反映 → 運用実験 → Web app方針、の順で確定させる。「STATUS」の命名は不適切として再考する

## 計画

### Phase 1: 概念・語彙の確定（完了）
- [x] 状態文書の名称決定 → **FOCUS.md**（STATUSは`whub status`と衝突するため不採用。「次に何に注力すべきか」と動機が一致）
- [x] FOCUS.mdの配置決定 → **`whub_data_dir()`直下に単一ファイル**（manifest.yaml/todos.yamlと同階層。`focus_path() = whub_data_dir()/"FOCUS.md"`をpaths.pyに追加）。vaultではなく「data-dir」に属する。data-dirが今vault配下にあるのは`config.toml`設定次第で、FOCUS自体はvault非依存
- [x] FOCUS.mdの持ち方決定 → **案1: 集約単一ファイル**（project別indexは持たない。mount/link不要で読める要件と一致）。manifestのprojectsと対応する代表状態説明を持つ
- [x] FOCUS.mdの構造確定 → **2層**（目標・価値観＝人間専用 ／ projects代表状態＝Agent半自動更新・manifest projects対応・「一言/現在地/停滞・締切」を持つ）。相談ログは同居させない（現在状態と過去履歴を混ぜない＋効果測定は実験期間限定なので計画md実行ログに残す）
- [x] roadmap「projectごとのindexファイル」項目の扱い → 当面FOCUS.mdへ吸収。独立項目は保留（「project視点の細かさが欲しい」と実際に困った時に案3ハイブリッドへ育てる）
- [x] todoの定義確定 → **project紐付けは任意・即閉じの独立アクション**（大学の事務書類提出・課題提出等を含む。非紐付けも許容するだけで紐付け禁止ではない）。FOCUSには影響しない
- [x] task-planning/roadmapの定義確定 → **project紐付き・FOCUS状態に影響する**。両者の起動/完了が**FOCUS更新トリガー**になるべき（下記トリガー設計）
- [x] FOCUS更新トリガーの設計決定 → **(b)プル型: 相談Skill1本が起動時にgit履歴＋roadmap差分＋todoから代表状態を再生成→推薦**。既存コマンド改造不要で実験を回せる。プッシュ型(a)は有効性が見えたら追加（→(c)）
- [x] 相談Skillの判断基準 → whub-concepts.md／workflow.mdに判断基準・機能の上下関係を文書化し、Skillは再定義せず参照（refileが`vault/readme.md`を参照するのと同型）
- [x] 投入口の粒度確定 → project非依存の思想・外部情報・一般ナレッジはinbox、project固有の構想・次にやりたいことはroadmapへ直接投げる。todoはproject紐付け任意で即閉じ、task-planning/roadmapはproject紐付きでFOCUSへ反映

### Phase 2: 文書反映（完了）
- [x] whub-concepts.mdを実装の正に整理（運用専用用語をworkflowへ移し、todo定義を修正、workflow委譲リンクを追加）
- [x] docs/workflow.md新規作成（運用の正: inbox/roadmapの投入口分担＋情報フロー＋Skill役割分担）
- [x] vault/readme.mdを構造と配置判断の正に整理（昇格・移動はworkflow/Skillへ委譲）
- [x] refile SKILL.mdの参照先をvault/readme.md＋workflow.mdへ付け替え（.agents/.claude両方）
- [x] docs/roadmapの「常設Webアプリ」「文脈付きStatus（→focus）」「projectごとのindex」を確定内容で書き直し

### Phase 3: 状態文書の運用実験（1〜2週間）
- [x] FOCUS.md初版を手動作成（Phase 1の2層構造に従う）
- [ ] 更新・相談Skill作成（git履歴・vault/todo・各roadmap参照→文書更新→推薦提示→承認/拒否を計画md実行ログに1行記録）
- [ ] 実験終了時にログで振り返り、半自動更新の要件と「推薦に従った率」を評価

### Phase 4: Web app最小版の方針決定
- [ ] 技術選定（Node許容前提。案: リポジトリ内`web/`を分離しVite系front＋Python APIサーバ、uv側の純正性は維持）
- [ ] 最小スコープ（inbox書込、roadmap書込、todo表示/追加、FOCUSビュー）を/execution-specで仕様化
- [ ] コンポーネント共通化・エクスポート基盤（roadmap「固有コンポーネント頒布」項目）との関係整理。portfolioのMarkdownRenderer.tsx流用可否もここで判断

## 実行ログ

### 試行 1: 壁打ちラウンド1〜2（2026-07-08）
- 実施内容: roadmap 3項目（投入口Webアプリ・文脈付きStatus・projectごとのindex）の統合可否と未決点をQ&A形式で整理
- 結果: 前提欄の各項目が確定。未決は命名・配置・構造・index統合・技術選定
- 判断: 続行（Phase 1の残り論点を壁打ちで確定させる）

### 試行 2: 命名・配置確定と基盤項目の発掘（2026-07-08）
- 実施内容: FOCUS命名決定、data-dir配置確定（実装のwhub_data_dir()と照合）、既存refile Skill・Fable活用法mdの現状確認
- 結果: 発散で3つの基盤項目が判明しroadmapへ追記（投入口整理／unknowns-field-guide統合／AGENTS・CLAUDE.md導線整備）。refileが既にinbox→todo/roadmapを逃がしている事実を確認。todo定義（project紐付け任意・即閉じ）とtask-planning/roadmap（project紐付き→FOCUS影響）を確定
- 判断: 続行（残るPhase 1論点はFOCUS構造とFOCUS更新トリガー設計の2点）

### 試行 3: FOCUS構造とトリガー確定・Phase 1クローズ（2026-07-08）
- 実施内容: FOCUS構造の3層案を提示→相談ログの位置づけを再検討、トリガー型を3案提示
- 結果: 相談ログをFOCUS本体から除外し2層に簡素化（効果測定は実験期間限定として計画md実行ログへ）。トリガーは(b)プル型の相談Skill1本に確定。判断基準はwhub-concepts.md／workflow.mdへ文書化しSkillが参照する方式
- 判断: Phase 1（概念設計）完了。Phase 2（文書化）へ

### 試行 4: 文書整理の設計（Phase 2実施→汚染テストによりリバート）（2026-07-08）
- 実施内容: whub-concepts.md肥大化を評価し、3文書分担を決定。concepts=実装の正（用語＋設計/振る舞いポリシー）、workflow.md（新規）=運用の正（inbox/roadmap/refile/discourse/focus・昇格フロー・vault配置判断・Skill役割分担）、vault/readme.md=構造の正。refileの判断基準参照先をworkflowへ付け替え、vaultの構造定義はreadmeを継続参照する方針
- 結果: 上記をファイルへ反映したが、コンテキスト汚染耐性テストの一環だったため全変更をリバート（roadmap.md／whub-concepts.md／本計画md／作成したworkflow.md・readme編集・refile編集）。slidesは別プロセスのため維持。本計画md自体は資産として復元
- 判断: 設計判断（3文書分担）は確定済み。クリーンなセッションでPhase 2を再実行する

### 試行 5: Phase 2文書反映の再実行（2026-07-08）
- 実施内容: workflow新設、whub-concepts整理、vault/readme整理、refile参照更新、roadmap旧語彙更新
- 結果: capture/backlog中間段を廃止し、project非依存はinbox、project固有はroadmapへ直接投げる方針へ統一
- 判断: Phase 2完了。Phase 3（FOCUS.md初版と相談Skill実験）へ

### 試行 6: FOCUS.md初版作成（2026-07-08）
- 実施内容: manifest projectsを元に`vault/whub/FOCUS.md`を作成し、各projectの現在状態サマリー欄を未記入で用意
- 結果: 推測の状態補完はせず、FOCUSの器だけ作成
- 判断: 続行（次は更新・相談Skillの設計）

## 結果
