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
- [ ] `whub task` — プロジェクト横断のタスク管理
    - `whub task`を叩いたら、やるべきToDoリストが出てきて、完了したらチェックがつく
    - 複数ワークスペースを統合したからこそ成立する、プロジェクト横断の一元管理
    - `mind/tasks.md`に、Obsidian起点で試行した痕跡があるが、CLIなら可搬性が高く軽量
- [ ] 自宅サーバのシャットダウンをwhubに組み込む
    - 寝る前にリモート接続して`sudo shutdown -h now`が面倒
- [ ] tailscale upの自動実行
    - 自宅サーバとの接続がVPNなので、接続確立を自動化したい

## whub アーキテクチャ・設定

- [ ] `whub`をグローバルコマンドとして登録すべきか検討
    - 現状はリポジトリ内でのみ動作。`~/.whub/`に設定を集約するなら、どこからでも叩けるようにする方が自然

## AIコンテキスト整備（boot / codegraph）

- [ ] 大きなMarkdownの読み込み効率化（md2idx的アプローチの導入）
    - 参考: https://zenn.dev/oubakiou/articles/b9db61885cd7be
    - MDファイルから見出しベースの目次インデックスを生成し、LLMが必要セクションだけを読めるようにする手法
    - 5000行のAPI仕様書でも目次→該当セクションのみ取得で80〜98%のトークン削減が見込める
    - `whub boot`で配布するCLAUDE.md/skillsに組み込めば、全リソースで統一的に使える
    - md2idx（npm）をそのまま使うか、同等のPython実装をwhubに内蔵するか要検討

## Agentルール・ドキュメント管理

- [ ] `source: human | ai | ai-edited` フラグをドキュメントに導入
    - AIによる勝手な仕様変更を防いで、人間が指定した仕様を忠実に守るようにしたい
- [ ] /task-planningスキルの更新
    - Obsidianイメージで、タスク間リンク・依存関係を記述可能にする
    - 作業Bが完了してからじゃないと作業Aには取りかかれない、だからAを始めようとした時にBを実施するよう促す
- [ ] /task-planningにおいて、過去に解決した課題とかに関する1行サマリーをMEMORY.mdに管理するのアリかも？
