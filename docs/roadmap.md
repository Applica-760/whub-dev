# workspace-hub Roadmap

## whub CLIの新機能・拡張

- [ ] リモート接続環境の整備（リモートファースト + SSHFS参照マウント）
    - 方針: 作業セッションはリモート主体（tmux）、mountは編集・コード確認・プロジェクト横断コンテキストのAI参照用。重い走査（CodeGraph等）はSSHでリモート実行し、レイテンシ弱点を踏まない
    - SSHFSマウントを復活 — `noappledouble`でAppleDouble遮断、`reconnect`系オプション＋staleマウント検知。旧実装をgit履歴（`490a40e^`）から回収
    - `whub cd`のremote時をtmuxセッションに拡張。Mac切断後もAgent・長時間処理が継続。複数クライアント同時接続はgrouped sessionで独立ビューを確保
    - `whub status`へtmuxセッション有無・マウント健全性を統合
    - `whub fetch <resource> <remote-path>` — 大容量ファイルを手元で確認する用途の逐次取得（sshfs経由コピーは低スループットのためscp直）。fetch先は`.whub/downloads/<resource>/`
    - 無人Agent運用のpermission設計（allowlist等）が別途必要
    - 適用はまず自宅サーバ限定。スパコンはログインノードの常駐プロセス制約があるため対象外
    - 前提: tailscale up自動化（接続確立がクリティカルパスに乗る）
    - 経緯（ADR化する）: AppleDouble汚染は`noappledouble`で回避。レイテンシ弱点は重い走査のリモート委譲により実質無効化と再評価しSSHFS復活。Mutagen双方向同期はリモートAgent稼働中のローカル編集で構造的コンフリクトが必然のため不採用。エディタリモーティングはプロプライエタリなvscode-server依存のため見送り。`whub edit`/`whub browse`はmountにより不要化
- [ ] `whub boot`の保守用ドキュメントを書く
    - 配布元、merge/json/skillsの処理、local/remote分岐、SSH・rsync・CodeGraph初期化の関係を記録する
- [ ] 思考キャプチャ・練り上げの仕組み（検討中）
    - 解きたい問題: 開発中に湧く雑多な思いつきを中断なく記録し、壁打ちを経て仕様レベルまで練り上げたい
    - 暫定方針: project未確定の思いつきは`mind`のRoadmapを全体inboxとして扱い、project固有の構想は各projectのroadmapへ入れる
    - `whub inbox`新設は、`whub roadmap mind`運用では扱いにくい未分類メモが増えた場合に再検討する
    - 追加方針: 雑な興味・ニュース・論文候補・会話由来メモはMarkdown化せず、まずJSONLの軽量インデックスへ蓄積する案を検討する
    - 役割分担: Agent/Skillは自然言語の会話から分類・要約・記録用メモを生成し、`whub`コマンドはproject/category/kind/source等を検証して決定的にJSONLへ追記する
    - 想定動線: ChatGPT/Codexで質問・壁打ち → 最後にcapture用Skillを起動 → Skillが文脈を要約して`whub capture add ...`を提示 → ユーザー承認後に実行
    - JSONL項目候補: `id`, `created_at`, `project`, `category`, `kind`, `title`, `source`, `note`, `tags`, `status`
    - 分類候補: `category=research|interest|idea|question|reference`, `kind=paper|news|web|book|thought|conversation`, `status=inbox|promoted|archived`
    - 位置づけ: JSONLは履歴・素材・低摩擦な投入口、Markdown/Literatureは整理済み知識として分担する
    - 候補A: `whub roadmap mind`で高速キャプチャ → skill/Agentで整理（whubにルーター機能を持たせすぎない）
    - 候補B: キャプチャ自体もskillに任せる（CLIコマンドは追加しない、`/brainstorm`的なskillで対話的に吐き出し→整理）
    - 候補C: mind側に独自アプリを構築し、whubとは疎結合にする
    - 関連: `whub todo`との境界、`/task-planning`・`/execution-spec`との責務分担も再検討が必要（下記参照）
- [ ] 常設キャプチャWebアプリの検討
    - 解きたい問題: `whub todo`や`whub status`を都度実行するだけだと起動・確認の摩擦があり、思考・todo・AI指示の記録漏れが起きやすい
    - 方針: `whub app`としてlocalhostのWeb UIを起動し、常設の入力口・一覧・軽い編集画面を提供する。TUI/Tkinterは主案から外し、必要時の補助に留める
    - 表示/操作候補: todo追加/完了、未整理メモ、AI指示草稿、project一覧、`whub status`の要約、後でAgentへ渡すキュー
    - 境界: ChatGPT/Codexの再実装はしない。GUIは捕まえる・並べる・軽く編集する・受け渡すまでを担い、解釈/分解/実装/整理はAgentやSkillへ委ねる
    - 初期スコープ: ローカルWeb UIでtodoとメモ/AI指示を保存できる最小版。Agent起動や自動実行は後段で検討する
- [ ] 常駐アプリで音声入力したい
- [ ] Twitterからのソース取得を円滑化する機能ほしい
- [ ] 自宅サーバのシャットダウンをwhubに組み込む
    - 寝る前にリモート接続して`sudo shutdown -h now`が面倒
- [ ] tailscale upの自動実行
    - 自宅サーバとの接続がVPNなので、接続確立を自動化したい
- [ ] `cd`と`status`のSSH異常系・終了コードの自動テスト
    - リモートリソース操作の実装は完了済み（SSHFS廃止、manifest分離、共通SSH基盤）
    - 残りはこのテスト追加のみ

## whub 実装改善（2026-07-03 コードレビューより）

優先度順。1〜3は互いに独立で既存テストを壊さず導入可能。

- [ ] whubルートの上方探索（CWD依存の解消）
    - `MANIFEST_PATH`・`TODO_PATH`・`workspace_path`解決がすべてCWD前提で、`whub cd`した先でwhubが使えない
    - gitと同様に`.whub/`を上方探索し、`WHUB_ROOT`環境変数をフォールバックにする。変更は`load_manifest()`と`TODO_PATH`に集約できる
- [ ] manifest読み込みエラーの整形と`version`のcoerce
    - manifest欠落・YAML不正・検証エラーで生tracebackが出る。`get_manifest`でClickExceptionに変換する
    - `version: 2`（非引用）がint扱いで検証失敗する。`Literal[2, "2"]`で受けるか文字列にcoerceする
- [ ] SSH ControlMaster導入（`build_ssh_command`に`-o ControlMaster=auto -o ControlPersist`）
    - statusはremote 1件につき逐次2接続（health+git、最悪16s/件）、boot remoteはファイル毎に往復している
    - 接続確立コストを初回1回に償却。あわせてstatusのhealth+gitの1コマンド結合、ThreadPool並列化も検討
- [x] 解決済みリソースの非Optional化（2026-07-03完了）
    - PrivateAttrのデフォルト除去で`_resolved_host`/`_resolved_workspace_path`を非Optional化し、到達不能なNoneガード13箇所を削除
    - 残課題: 検証と実行環境解決の分離（`load_manifest()`が解決済みビューを返す構造）はCWD依存解消と合わせて検討
- [ ] managed-blockロジックの統合（3実装 → 1モジュール）
    - boot `_managed_range`・roadmap `_insert_memo`・link `_update_gitignore`が別実装
    - link版は空行終端頼みで、ブロック直後に空行なしで行を足すと次回link時に消えるバグ候補。boot版ベースで統合する
- [ ] boot skills配布の削除伝播
    - local `copytree(dirs_exist_ok)` / remote `rsync -a`（--deleteなし）のため廃止Skillが残骸として残り続ける
    - remoteは`--delete`、localは配布先を消してからcopyで揃える
- [ ] 小粒の修正
    - `build_rsync_command`のidentityパス未引用（空白入りパスで壊れる）
    - roadmapのremote未対応がexit 0で成功風に終わる
    - statusのgit列「-」が「git未設定」と「取得失敗」を区別できない
    - shell-initの補完生成が毎シェル起動でPythonを起動する（ファイルキャッシュ化）
    - `--version`未実装、`_parse_due_date`年またぎとlink gitignore編集のテスト未カバー
    - roadmapのworkspace-hub特別扱いがコンセプト文書「bootだけ例外」と不整合（文書か実装を揃える）

## whub アーキテクチャ・設定

- [ ] projectごとの長期計画ドキュメントとwhub導線を設計する
    - これまでの方針: `whub todo`で全体のタスクと優先度、`whub status`で接続状態を確認し、`whub cd`で対象projectへ移動する
    - todoは実行可能な単発アクション、roadmapはprojectごとの長期方針、`/task-planning`は個別作業の実行計画と記録を担う
    - longterm-todoのproject固有項目は、whub todo運用が安定してから各projectのroadmapへ段階的に移行する
    - `whub roadmap <project> <text...>`で`<project>/docs/roadmap.md`末尾の未整理メモへ追記する
    - `init`や`list`は作らず、本文なし実行はエラーにする
    - roadmap上部は整理済みロードマップ、末尾は未整理メモの投入口としてテンプレートで明確に分ける
    - 壁打ち、計画の構造化、specs/ADRへの昇華はCLIではなくSkill/Agent側に任せる
- [ ] projectごとの1行サマリ/indexファイルを検討する
    - 解きたい問題: whubからprojectへ入るAgentが、リポジトリ全体を読む前に「何のprojectか」「今どこを見るべきか」を短時間で把握できる入口がほしい
    - 候補: 各projectに短いindexファイルを置き、1行サマリ、主要ドキュメント、現在の主タスク、roadmap/todo/specsへの導線を定義する
    - whub側の役割: `whub status`や常設フォーカス画面でこのサマリを表示し、Agent起動時の入口として参照させる
    - 未決: ファイル名、配置場所、manifestへ持たせるか各project内に置くか、bootでテンプレート配布するか
- [ ] `whub`をグローバルコマンドとして登録すべきか検討
    - 現状はリポジトリ内でのみ動作。`~/.whub/`に設定を集約するなら、どこからでも叩けるようにする方が自然

## AIコンテキスト整備（boot / codegraph）

- [ ] 大きなMarkdownの読み込み効率化（md2idx的アプローチの導入）
    - 参考: https://zenn.dev/oubakiou/articles/b9db61885cd7be
    - MDファイルから見出しベースの目次インデックスを生成し、LLMが必要セクションだけを読めるようにする手法
    - 5000行のAPI仕様書でも目次→該当セクションのみ取得で80〜98%のトークン削減が見込める
    - `whub boot`で配布するCLAUDE.md/skillsに組み込めば、全リソースで統一的に使える
    - md2idx（npm）をそのまま使うか、同等のPython実装をwhubに内蔵するか要検討

## mind — 思考整理（検討中）

- [ ] mindの位置づけと仕組みの決定
    - 現状: Obsidianベースの個人ナレッジ（`00_inbox` → `02_Concept` → `03_Permanent`のZettelkasten的フロー）
    - 暫定運用: project未確定の思いつきは`mind`のRoadmapを全体inboxとして扱う
    - 追加案: `mind`配下に興味・文献候補・ニュース由来のJSONLインデックスを置き、project紐付けや`research`/`interest`等の分類で後から引けるようにする
    - Literatureとの関係: JSONLは未整理・軽量な履歴、`Literature`は論文として読む/育てる価値が出た項目の昇格先とする
    - whubとの実装上の関係は未決: 独立アプリ化するか、skillsで十分か、whubに統合するか
    - 上記「思考キャプチャ・練り上げ」の方針決定と連動する
- [ ] 個人向け学問領域テキスト生成・知識整理プロジェクト（検討中）
    - 目的: 自分が興味を持つ学問領域について、DeepResearch等で継続調査し、自分専用の教科書・知識体系として育てる
    - 基本サイクル: 寝る前に1つの問いを調査依頼 → 翌朝に出典・論点・誤りを確認 → 修正・追加調査 → 週次で章立てや概念体系へ再編する
    - 位置づけ: mindプロジェクトの`Literature`を拡張し、文献要約だけでなく、問い・概念・主張・論争・未解決問題・自分のレビューを扱う
    - 方針: AIに直接「完成教科書」を書かせるのではなく、出典付き知識ベースを育て、その上に`Textbook`ビューを生成する
    - 保存単位候補: `Questions`、`Concepts`、`Literature`、`Claims`、`Debates`、`Textbook`、`Review Notes`
    - 必須メタ情報: 出典、信頼度、関連する問い、人間確認済みか、未検証仮説か、次に調べること
    - 主なリスク: 重要文献の抜け、誤った重み付け、もっともらしい誤説明の蓄積、確認作業が受け身の読書ログになること
    - MVP: まず1分野に限定し、毎晩1問だけ調査、翌朝に出典・重要概念・疑問点を確認し、週1で章構成へ反映する

## Agentルール・Skills体系

- [ ] `source: human | ai | ai-edited` フラグをドキュメントに導入
    - AIによる勝手な仕様変更を防いで、人間が指定した仕様を忠実に守るようにしたい
- [ ] Skills体系の再設計（検討中）
    - 現行: `/task-planning`（計画・記録）、`/execution-spec`（仕様書）、`/issue-log`（issue記録）
    - 課題: 「雑なアイデア→壁打ち→方針整理→仕様化→実装指示」の流れの中で、どのskillがどこを担うか曖昧
    - 検討候補:
        - `/brainstorm`的な壁打ちskillを新設し、task-planningとexecution-specの前段に置く
        - task-planningとexecution-specの責務境界を再定義する（計画 vs 仕様 の線引き）
        - `/whub-xxx`としてwhub固有skillsをboot配布する（他プロジェクトでも共通利用）
    - 関連: whub todoとの連携（todoから詳細を詰めたい→skillで壁打ち→仕様に昇格、の導線）
- [ ] コンセプト・位置づけ・責務を対話で固める壁打ちSkillを作る
    - todo着手後、task-planningや実装計画へ進む前に使い、目的・境界・用語・トレードオフを整理する
- [ ] 壁打ちで確定した方向性やディテールをspecs・ADRへ昇華するトリガーを設計する
    - 重要な仕様や設計判断が確定した時点で、対話内容を永続的な仕様・意思決定記録へ変換する
- [ ] /task-planningにおいて、過去に解決した課題とかに関する1行サマリーをMEMORY.mdに管理するのアリかも？

<!-- hub:roadmap:appended:start -->
<!-- hub:roadmap:appended:end -->
