## whub CLIの新機能・拡張

- [ ] リモート運用の残課題
    - 無人Agent運用のpermission設計（uv allowlistは`docs/tasks/`で進行中）
    - tailscale up自動化（自宅サーバとの接続確立）
    - 自宅サーバのシャットダウンをwhubに組み込む
    - `cd`と`status`のSSH異常系・終了コードの自動テスト
    - SSHFS復活・tmux運用・Mutagen不採用などの経緯をADR化する
- [ ] whub appの残機能
    - FOCUSビュー（FOCUS.md再構成タスクの決着後）
    - スマホから質問・思いつきをinbox/backlogへ投げられるようにする
    - discourse連携ビュー: 解説結果を眺め、skip/keep/noteやinbox/backlog/todo/literatureへの振り分けを行う
    - 音声入力
    - statusにwhub appの起動状況モニタを入れる
- [ ] boot skills配布の削除伝播
    - local `copytree(dirs_exist_ok)` / remote `rsync -a`（--deleteなし）のため廃止Skillが残骸として残り続ける
    - remoteは`--delete`、localは配布先を消してからcopyで揃える

## whub アーキテクチャ・設定

- [ ] 意思決定・設計方針・判断基準・運用ルールの文書化を整備する（ミノ駆動などを参考に）

## AIコンテキスト整備（boot / codegraph）

- [ ] 大きなMarkdownの読み込み効率化（md2idx的アプローチの導入）
    - 見出しベースの目次インデックスを生成し、LLMが必要セクションだけ読めるようにする（参考: https://zenn.dev/oubakiou/articles/b9db61885cd7be）
    - `whub boot`配布物に組み込むか、md2idx（npm）採用かPython内蔵かは要検討
- [ ] 私の固有コンポーネント（スライド・Web等）を共通化し、bootと同様に頒布する仕組みを作る

## vault（旧mind） — 私のデータの貯蔵庫

- [ ] ADR-0008の後続タスク
    - recruit由来文書（志向・自己分析）の整理: vaultに志向の本体、recruitに派生文書
    - workspace-hub公開前のgit履歴scrub（過去のmanifest・todosが履歴に残存）
- [ ] 個人向け学問領域テキスト生成・知識整理プロジェクト（検討中）
    - 目的: 興味を持つ学問領域をDeepResearch等で継続調査し、出典付き知識ベースを育てて`Textbook`ビューを生成する（AIに完成教科書を直接書かせない）
    - MVP: 1分野に限定し、毎晩1問調査 → 翌朝に出典・重要概念・疑問点を確認 → 週1で章構成へ反映
    - 主なリスク: 重要文献の抜け、もっともらしい誤説明の蓄積、確認作業が受け身の読書ログになること
- [ ] レートリミットの有効活用: 寝る前にルールベースのinbox自動整理を走らせる案
    - 複雑な設計判断はAgentに委ねず、分類・振り分け候補提示など安全な範囲に留める
- [ ] daily / FOCUS の日次振り返り運用（Obsidian Daily相当、vault連携前提）
    - その日の終わりにgit差分・todo・backlogの消化度合いからサマリーと感想を作り、前進感を得られるようにする
    - 発展: Web appで履歴を見られるようにし、グラフ等で成長を可視化する

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

<!-- hub:backlog:appended:start -->
- HTMLビュー/Markdownレンダラー導入
- vaultエクスプローラーがあれば、inboxとの連携性高まりそう
- プロジェクトごとのページではなく、whubを特別扱いしたPageとして、conceptやworkflowをタブの一つに入れることで、運用、設計に迷った時の指針になりそう
- todoのedit機能をwebappにも導入
- task mdのビューも追加したら、噛み砕いた作業単位はwebappで一望できるようになるはず。Backlogと合わせて、「プロジェクトの情報を見る」ようなWidgetFrameができたらいい
- ダークモード実装
<!-- hub:backlog:appended:end -->
