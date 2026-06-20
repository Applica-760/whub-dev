<!-- /task-planning Skills を補強する長期スパンでやりたいこと -->

- [x] CLAUDE.mdの「一般指示」と「プロジェクト固有のインストラクション」を分離 → ADR-0006（マーカー方式）
- [ ] hub sync実行時にhub contextを自動実行し、状態サマリーを自動生成する
- [ ] hub sync時にCodegraph indexの一括再生成もトリガーし、AIコンテキストを自動整備する
- [ ] 寝る前に自宅のサーバの電源を落とすが、リモート接続して`sudo shutdown -h now`が面倒。`whub`コマンドに組み込めれば楽かも？
- [ ] tailscale up とかも自動で実行するようにしたい。自宅サーバとの接続がVPNなので