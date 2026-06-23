<!-- /task-planning Skills を補強する長期スパンでやりたいこと -->

## whub CLIの新機能・拡張

- [ ] リモートファイルのオンデマンド操作（SSHFS廃止の代替、方向A: オンデマンドSFTP方式）
    - SSHFSのマウント方式はApple Doubleファイル汚染・boot遅延の原因だったため廃止。代わりにscp/ssh subprocessベースでオンデマンドにファイルを取得・編集する
    - 既存の`remote.py`（`run_ssh_command` / `build_ssh_command`）をそのまま活用し、paramiko等の依存追加は不要
    - `whub fetch <resource> <remote-path>` — scpでファイル取得。fetch先は`.whub/downloads/<resource>/`
    - `whub edit <resource> <remote-path>` — scp取得→$EDITORで開く→mtime変更検知→書き戻し
    - `whub browse <resource>` — TUIファイルブラウザ。自前curses or filessh等の外部ツールラップ。優先度低、fetch/editで運用してから判断
    - 検討済み代替案: Mutagen（双方向リアルタイム同期）は大容量データセットに不向き、filessh/termscp（既存TUIツール）はマニフェスト統合がない
- [ ] `whub boot`の保守用ドキュメントを書く
    - 配布元、merge/json/skillsの処理、local/remote分岐、SSH・rsync・CodeGraph初期化の関係を記録する
- [ ] `whub todo` — プロジェクト横断のタスク管理
    - `whub todo`を叩いたら、やるべきToDoリストが出てきて、完了したらチェックがつく
    - 複数ワークスペースを統合したからこそ成立する、プロジェクト横断の一元管理
    - `mind/tasks.md`に、Obsidian起点で試行した痕跡があるが、CLIなら可搬性が高く軽量
    - 実装要素: `~/.whub/todos.yaml`のPydanticモデル + load/save、curses TUI（Add/Done/Delete/View completed）、resource補完（manifest連携）、priority色分け表示
    - statusのpriorityを廃止して、
        - `status`はリンク、接続状態の確認、git差分(未commit/pushがないかの確認)に留めて、
        - `todo`側に、todo管理、優先度把握を任せる
        - という構成にするといいのでは？

- [ ] 思考キャプチャ・練り上げの仕組み（検討中）
    - 解きたい問題: 開発中に湧く雑多な思いつきを中断なく記録し、壁打ちを経て仕様レベルまで練り上げたい
    - CLIコマンド（`whub inbox`等）で持つか、mind側のアプリとするか、skillsだけで回すかは未決
    - 候補A: `whub inbox` CLIで高速キャプチャ → skillで整理（whubにルーター機能を持たせる）
    - 候補B: キャプチャ自体もskillに任せる（CLIコマンドは追加しない、`/brainstorm`的なskillで対話的に吐き出し→整理）
    - 候補C: mind側に独自アプリを構築し、whubとは疎結合にする
    - 関連: `whub todo`との境界、`/task-planning`・`/execution-spec`との責務分担も再検討が必要（下記参照）
- [ ] 自宅サーバのシャットダウンをwhubに組み込む
    - 寝る前にリモート接続して`sudo shutdown -h now`が面倒
- [ ] tailscale upの自動実行
    - 自宅サーバとの接続がVPNなので、接続確立を自動化したい
- [ ] `cd`と`status`のSSH異常系・終了コードの自動テスト
    - リモートリソース操作の実装は完了済み（SSHFS廃止、manifest分離、共通SSH基盤）
    - 残りはこのテスト追加のみ

## whub アーキテクチャ・設定

- [ ] projectとresourceの概念・命名・関連付けを整理する
    - resourceは操作対象、projectはTodoの活動単位であり、現状はTodoのprojectをresource名に限定している
    - workspace-hub自身がresourceではないためwhub開発Todoを割り当てられず、複数resourceを1projectに束ねる表現もできない
    - manifestへのproject定義追加と、resourceからprojectへの任意の関連付けを検討する
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
    - whubとの関係は未決: 独立アプリ化するか、skillsで十分か、whubに統合するか
    - 上記「思考キャプチャ・練り上げ」の方針決定と連動する

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
