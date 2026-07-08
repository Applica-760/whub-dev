# workspace-hub Backlog

## whub CLIの新機能・拡張

- [ ] リモート運用の残課題
    - 無人Agent運用のpermission設計（allowlist等）
    - tailscale up自動化（自宅サーバとの接続確立）
    - 自宅サーバのシャットダウンをwhubに組み込む
    - `cd`と`status`のSSH異常系・終了コードの自動テスト
    - SSHFS復活・tmux運用・Mutagen不採用などの経緯をADR化する
- [ ] 常設Webアプリ / 投入口・todo・FOCUSビュー
    - 解きたい問題: `whub todo`や`whub status`を都度実行するだけだと起動・確認の摩擦があり、思考・todo・AI指示の記録漏れが起きやすい
    - 方針: `whub app`としてlocalhostのWeb UIを起動し、常設の入力口・一覧・軽い編集画面を提供する
    - 投入口: project非依存の思想・外部情報・一般ナレッジは`vault/inbox/`、project固有の構想は各`backlog`へ直接書く
    - 表示/操作候補: todo追加/完了、inbox、backlog、project一覧、FOCUSビュー
    - 境界: ChatGPT/Codexの再実装はしない。GUIは捕まえる・並べる・軽く編集する・受け渡すまでを担い、解釈/分解/実装/整理はAgentやSkillへ委ねる
    - 初期スコープ: inbox書込、backlog書込、todo表示/追加、FOCUSビュー
    - スマホ対応: 質問・思いつきをinboxまたはbacklogへ投げられるようにする
    - discourse連携ビュー: discourseの解説結果をHTML/GUIで眺め、skip/keep/noteやinbox/backlog/todo/literatureへの振り分けを行う
- [ ] 常駐アプリで音声入力したい

## whub 実装改善（2026-07-03 コードレビューより）

優先度順。上位項目は互いに独立で既存テストを壊さず導入可能。

- [ ] SSH ControlMaster導入（`build_ssh_command`に`-o ControlMaster=auto -o ControlPersist`）
    - statusはremote 1件につき逐次2接続（health+git、最悪16s/件）、boot remoteはファイル毎に往復している
    - 接続確立コストを初回1回に償却。あわせてstatusのhealth+gitの1コマンド結合、ThreadPool並列化も検討
- [ ] boot skills配布の削除伝播
    - local `copytree(dirs_exist_ok)` / remote `rsync -a`（--deleteなし）のため廃止Skillが残骸として残り続ける
    - remoteは`--delete`、localは配布先を消してからcopyで揃える
- [ ] 小粒の修正
    - shell-initの補完生成が毎シェル起動でPythonを起動する（ファイルキャッシュ化）
    - backlogのworkspace-hub特別扱いがコンセプト文書「bootだけ例外」と不整合（文書か実装を揃える）

## whub アーキテクチャ・設定

- [ ] FOCUS.mdによるproject代表状態の集約
    - 解きたい問題: whubからprojectへ入るAgentが、リポジトリ全体を読む前に「何のprojectか」「今どこを見るべきか」を短時間で把握できる入口がほしい
    - 方針: projectごとのindexファイルは当面持たず、`FOCUS.md`のproject代表状態へ吸収する
    - 配置: `whub_data_dir()`直下の単一ファイル
    - 保留: project視点の細かさが必要になったら独立indexを再検討する

## AIコンテキスト整備（boot / codegraph）

- [ ] 大きなMarkdownの読み込み効率化（md2idx的アプローチの導入）
    - 参考: https://zenn.dev/oubakiou/articles/b9db61885cd7be
    - MDファイルから見出しベースの目次インデックスを生成し、LLMが必要セクションだけを読めるようにする手法
    - 5000行のAPI仕様書でも目次→該当セクションのみ取得で80〜98%のトークン削減が見込める
    - `whub boot`で配布するCLAUDE.md/skillsに組み込めば、全リソースで統一的に使える
    - md2idx（npm）をそのまま使うか、同等のPython実装をwhubに内蔵するか要検討
- [ ] 私の固有コンポーネント（スライド・Web等）を共通化し、bootと同様に頒布する仕組みを作る

## vault（旧mind） — 私のデータの貯蔵庫

- [ ] ADR-0008の後続タスク
    - recruit由来文書（志向・自己分析）の整理: vaultに志向の本体、recruitに派生文書
    - workspace-hub公開前のgit履歴scrub（過去のmanifest・todosが履歴に残存）
    - 常設Webアプリのinboxを`vault/inbox/`に書く設計で統一（inbox×2の解消）
- [ ] 個人向け学問領域テキスト生成・知識整理プロジェクト（検討中）
    - 目的: 自分が興味を持つ学問領域について、DeepResearch等で継続調査し、自分専用の教科書・知識体系として育てる
    - 基本サイクル: 寝る前に1つの問いを調査依頼 → 翌朝に出典・論点・誤りを確認 → 修正・追加調査 → 週次で章立てや概念体系へ再編する
    - 位置づけ: mindプロジェクトの`Literature`を拡張し、文献要約だけでなく、問い・概念・主張・論争・未解決問題・自分のレビューを扱う
    - 方針: AIに直接「完成教科書」を書かせるのではなく、出典付き知識ベースを育て、その上に`Textbook`ビューを生成する
    - 保存単位候補: `Questions`、`Concepts`、`Literature`、`Claims`、`Debates`、`Textbook`、`Review Notes`
    - 必須メタ情報: 出典、信頼度、関連する問い、人間確認済みか、未検証仮説か、次に調べること
    - 主なリスク: 重要文献の抜け、誤った重み付け、もっともらしい誤説明の蓄積、確認作業が受け身の読書ログになること
    - MVP: まず1分野に限定し、毎晩1問だけ調査、翌朝に出典・重要概念・疑問点を確認し、週1で章構成へ反映する
- [ ] レートリミットの有効活用: 寝る前にルールベースのinbox自動整理を走らせる案
    - 複雑な設計判断はAgentに委ねず、ルールベースで安全に処理できる範囲（分類・振り分け候補提示など）に留める
- [ ] daily / FOCUS の日次振り返り運用
    - 解きたい問題: vault dailyの運用方法とFOCUSの定期更新タイミングが浮いている
    - 方針: その日の終わりにgit差分、todo、backlogの消化度合いからサマリーと感想を作る
    - 期待: 蓄積により前進感・達成感を得られるようにする
    - 発展: Web appで履歴を見られるようにし、グラフ等で成長を可視化する

## Agentルール・Skills体系

- [ ] skill・agent rulesを1プロジェクト内でも一元化する
    - ClaudeとCodexの設定を二箇所で管理している状態を、シンボリックリンク等で解消したい
- [ ] `source: human | ai | ai-edited` フラグをドキュメントに導入
    - AIによる勝手な仕様変更を防いで、人間が指定した仕様を忠実に守るようにしたい
- [ ] Skills体系の再設計（検討中）
    - 現行: `/task-planning`（計画・記録）、`/execution-spec`（仕様書）、`/issue-log`（issue記録）
    - web appのinbox/backlog/todoフローと連動して、壁打ち・仕様化・実装計画の担当を決める
    - `/brainstorm`的な前段Skillや、whub固有Skillのboot配布を検討する
- [ ] コンセプト・位置づけ・責務を対話で固める壁打ちSkillを作る
    - todo着手後、task-planningや実装計画へ進む前に使い、目的・境界・用語・トレードオフを整理する
- [ ] 壁打ちで確定した方向性やディテールをspecs・ADRへ昇華するトリガーを設計する
    - 重要な仕様や設計判断が確定した時点で、対話内容を永続的な仕様・意思決定記録へ変換する
- [ ] /task-planningにおいて、過去に解決した課題とかに関する1行サマリーをMEMORY.mdに管理するのアリかも？

<!-- hub:backlog:appended:start -->
<!-- hub:backlog:appended:end -->
