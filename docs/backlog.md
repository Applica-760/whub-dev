## whub CLIの新機能・拡張

- [ ] リモート運用の残課題
    - tailscale up自動化（自宅サーバとの接続確立）
    - 自宅サーバのシャットダウンをwhubに組み込む
    - `cd`と`status`のSSH異常系・終了コードの自動テスト
    - SSHFS復活・tmux運用・Mutagen不採用などの経緯をADR化する
- [ ] whub appの残機能
    - スマホからinbox/backlogへ投げるためのアクセス経路（LAN公開 or Tailscale経由）。入力フォームのWeb UIとPOST APIは実装済み
    - discourse連携ビュー: 解説結果を眺め、skip/keep/noteやinbox/backlog/todo/literatureへの振り分けを行う
        - URL投入→headless Claude（`claude -p` or Agent SDK）を非同期ジョブで起動し、`vault/literature/pending/`へ解説mdを出力（frontmatterにurl/type/summary/提案tags/session_id）
        - verdictボタンの確定処理（log.jsonl追記・md移動/削除）はAgentを使わずservices層のPythonで実装し整合性を保証
        - noteのみ追加で`--resume <session_id>`によりClaudeを再起動し、記事全文の文脈を保持したままnote本文を生成
        - 発展: Web上の簡易チャットを同session resumeに乗せ、壁打ち→note昇格の体験を再現
        - 論点: Web appからvault/literatureへの書き込み解禁はADR化、新規タグはUI上でマーク表示して統制語彙の崩れを防ぐ
    - 音声入力
    - statusにwhub appの起動状況モニタを入れる
    - whubを特別扱いしたPageにconceptやworkflowのビューをタブで入れ、運用・設計に迷った時の指針にする（Knowledgeタブは実装済み）
    - todoのedit機能をweb appにも導入
    - task mdビューを追加し、BacklogやTodoと合わせて「プロジェクトの情報を見る」WidgetFrameを作る（ロードマップビューはTASK-003 `docs/tasks/20260715_1554`で進行中）
    - backlogを追加した時にweb appでエフェクトを出す
- [ ] whub knowledge CLIの残り（`check`・`query`とWeb appのKnowledgeビューは実装済み）
    - 発見性: AgentにCLIを呼ばせる誘導はCLAUDE.md側のトリガー条件付き平文（「whub/データモデル変更前に`whub knowledge query <対象>`」）が必要
    - 作らない: 全件dumpする素通しの`ls`はReadと等価でCLI化の意味がない
- [ ] boot skills配布の削除伝播
    - local `copytree(dirs_exist_ok)` / remote `rsync -a`（--deleteなし）のため廃止Skillが残骸として残り続ける
    - remoteは`--delete`、localは配布先を消してからcopyで揃える
- [ ] wflow Taskの計画変更を安全に反映するCLIを追加する
    - `request_plan_change`で理由を記録して`draft`へ戻した後、改訂したplan全体を`wflow task plan replace TASK --file PLAN.yaml`で検証・原子的に反映する
    - Phase／Stepを逐次編集するCLIは、順序ベースの`PPP-SSS`参照を途中挿入で変え、個別操作ごとの中間状態も増やすため、初期実装では設けない
    - 反映時は承認・受け入れ結果を失効させ、再承認を必須にする。完了済みPhase／Stepは実績として不変にし、未完了部分だけを変更対象にする
    - Task YAMLの直編集を禁止せず、plan断片の記述とレビューにはYAMLを使う。Task YAMLへの反映・整合性検査・履歴管理はCLIへ一本化する

## whub アーキテクチャ・設定

- [ ] 意思決定・設計方針・判断基準・運用ルールの文書化を整備する（ミノ駆動などを参考に）
- [ ] workspace-hub公開前のgit履歴scrub（過去のmanifest・todosが履歴に残存、ADR-0008の後続）

## AIコンテキスト整備（boot / codegraph）

- [ ] 大きなMarkdownの読み込み効率化（md2idx的アプローチの導入）
    - 見出しベースの目次インデックスを生成し、LLMが必要セクションだけ読めるようにする（参考: https://zenn.dev/oubakiou/articles/b9db61885cd7be）
    - `whub boot`配布物に組み込むか、md2idx（npm）採用かPython内蔵かは要検討
- [ ] 私の固有コンポーネント（スライド・Web等）を共通化し、bootと同様に頒布する仕組みを作る

## 運用・振り返り

- [ ] レートリミットの有効活用: 寝る前にルールベースのinbox自動整理を走らせる案
    - 複雑な設計判断はAgentに委ねず、分類・振り分け候補提示など安全な範囲に留める
    - 寝る前に実行し、Skill記述の陳腐化やドキュメント更新が追いついていない箇所を検査する仕組みも同枠で走らせる
- [ ] dailyの日次振り返り運用（Obsidian Daily相当、vault連携前提）
    - その日の終わりにgit差分・todo・backlogの消化度合いからサマリーと感想を作り、前進感を得られるようにする
    - 発展: Web appで履歴を見られるようにし、グラフ等で成長を可視化する
    - 必要性の裏付け（2026-07-15）: 直近1ヶ月のgit履歴・Claude/Codexセッションログを手動集計したところ、休息日ゼロ・活動の28%が21時〜深夜2時台という稼働過多を初めて客観視できた（`vault/inbox/20260715_直近1ヶ月の開発量サマリ.md`）
    - 前進感の可視化だけでなく、稼働過多の早期検知・「今日はもう十分」の判断材料としても機能させる
    - 消化したタスクの表示・消化量のグラフ化で、その日どれだけ前に進めたかの認知を深める
    - 時計機能やCommit回数・実装量から「自分基準で1日あたりこのくらい活動できていれば十分」の基準を作り、際限なくがんばる負荷を防ぐ
    - データソースはgit log＋`~/.claude/projects`・`~/.codex/sessions`のログファイル日時集計で足りることを確認済み
    - アイデア: VS Code拡張で編集・保存・統合ターミナル実行・ウィンドウフォーカスをローカル集計し、能動時間・Task別時間・長時間連続作業の休憩候補を表示する。カメラ計測は初期対象外

## Agentルール・Skills体系

- [ ] skill・agent rulesを1プロジェクト内でも一元化する（Claude/Codex設定の二重管理をsymlink等で解消）
- [ ] `source: human | ai | ai-edited` フラグをドキュメントに導入し、人間が指定した仕様をAIが勝手に変更しないようにする
- [ ] Skills体系の再設計（検討中）
    - web appのinbox/backlog/todoフローと連動して、壁打ち・仕様化・実装計画の担当を決める
    - 壁打ち・相談系Skill: todo着手後、task-planningへ進む前に目的・境界・用語・トレードオフを整理する。会話履歴はvaultへ蓄積する
    - 壁打ちで確定した方向性・仕様をspecs・ADRへ昇華するトリガーを設計する
    - 傾聴モード・単純な調べごとモードなど、プロジェクト文脈が不要なSkill
    - whub固有Skillのboot配布
    - /task-planningで過去に解決した課題の1行サマリーをMEMORY.mdに管理する案
- [ ] ADR起票・knowledge.yaml更新のワークフロー組み込みとKnowledge連携TDD
    - 実装系TaskはKnowledgeの該当CON/POLを引きながらacceptanceを埋めてからapprove_planする
    - テストコードにDEF/CON対応のコメントを付け、Knowledge→acceptance→テストの導出関係を作る

<!-- hub:backlog:appended:start -->
- せめてtaskのページはホットリロードにしたい
- リロード時にスクロール位置を保持したい
- タスクをCompletedする時に、KnowledgeやBacklogに更新する点がないか調べるトリガーを置きたい
- InterruptしたタスクがCompleteしてもタスク間グラフビューに残り続ける
- 結局YamlがAgentから見えるから、.agentsignoreとかできたらいいな
- Knowledge YAMLとTask YAMLの配置を将来再検討する。docs/knowledge.yamlは確定済みのプロジェクト知識・仕様SSOTとしてdocs配置が妥当。一方、Task YAMLはstate・進捗・log・依存をCLIが更新する実行記録であり、docs/tasksより.wflow/tasks等のrepository-localなワークフローデータ領域へ分離する方が責務は明確になる。既存の凍結済みMarkdown履歴はdocs/tasks/doneに残す案を含め、可読性・Agentの発見性・移行コストと合わせて判断する。
- バイトの稼働管理できるタイマーあればいいな
<!-- hub:backlog:appended:end -->
