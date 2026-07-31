# Agent workspace task candidates

whub appを、単一利用者が複数のCoding Agentを監督・操作する主要インターフェースへ段階的に移行するための候補一覧。実装順・Task間依存・受け入れ条件はTASK-062で確定する。

理想：https://zenn.dev/singularity/articles/diy-terminal-500-commits

## Fixed premises

- `1 Task = 1 worktree = 1 Agent session` とする。
- Agent sessionはtmuxで維持し、ブラウザを閉じても実行を継続する。
- 主な利用環境はMac、スマホは監視・質問への回答など部分操作に限定する。
- 単一利用者向けとし、複数人利用・外部公開・完全自律実行は対象外とする。
- VS Codeからの段階的移行を許容し、初期のfile explorerは閲覧専用とする。

## Task candidates

記事の中心である「人が探しに行く」のではなく、Agentの状態・依頼文・通知によって「Agentに呼ばれる」体験を優先する。ブラウザ端末はそのための対話面であり、目的そのものではない。

### A. 並列実行を一意に管理する

1. worktreeのライフサイクルと命名規約を定義する
   - Task、worktree、Agent sessionの一意な対応と、作成・再利用・終了・削除の条件を決める。

2. `whub worktree` でworktreeを決定論的に操作する
   - git worktreeの作成・一覧・切替・削除と、対応するproject symlinkの作成を扱う。

3. worktreeをproject resourceとして認識・状態表示する
   - 元projectとの関係、branch、mount状態、作業pathを利用者が把握できるようにする。

4. Task、worktree、Agent sessionの対応を保存・検証する
   - 再接続・復旧・削除時に対応関係が失われないことを保証する。
   - 稼働中の対応sessionを検出し、worktree削除を拒否する。

### B. Agentを対話・監督する

5. CodexとClaude CodeのAgent adapterを定義する
   - 起動、再接続、終了、共通状態の報告に必要な最小契約を定める。

6. Agent実行ハーネスを整備する⭐️
   - Task、worktree、tmux sessionに対応するAgentの起動、停止、再接続、実行記録を一貫して扱う。
   - Agentが計画を編集するのは`--actor agent`で承認するが、最終的なcompleteやそもそもの起票は人間だけにする
   - worktree以下のディレクトリは任意の編集をしていいが（gitのブランチに過ぎないので）、それより上の階層への編集権は与えないとか
   - `.codex/rules/default.rules` `.claude/settings.local.json`みたいに細かいコマンド制御を、ロール毎に頒布可能な形で定義する

7. Agent lifecycle hooksを整備する
   - 起動、状態変化、質問、権限要求、終了を構造化してcontrol planeへ通知する。

8. Agentのロールと権限プロファイルを定義する
   - 実装・PR作成などの限定操作と、削除・build・mergeなどの強い操作を分離する。
   - 権限要求を共通イベントとして扱い、UIの`権限待ち`表示へ接続する。

9. Agentの共通状態を収集する
   - [session state](session-state.md)の契約へ、adapterからAgent固有の出力を正規化して取得する。

10. 複数Agentの監督画面を実装する
   - Task、worktree、依頼文、共通状態を一望し、対応が必要なsessionを優先表示する。
   - 状態、依頼文、summary、色、通知を用いて、利用者がsessionを探さなくてよい状態を目指す。

11. tmux sessionをWebから安全に入出力する接続基盤を作る
   - ブラウザ切断後の継続、再接続、resize、入力経路、単一利用者向け認証を扱う。

12. ブラウザ内ターミナルを実装する
    - tmux sessionへ対話接続し、既存Agentとの会話を継続できるようにする。

13. Agentとの継続会話をWeb UIで扱う
    - CodexまたはClaude Codeとの会話を開始・再開し、質問への回答を送れるようにする。

### C. 開発環境を段階的に移行する

14. hub内file explorerを実装する
    - 初期段階では閲覧専用とし、編集機能は後続の段階的移行で検討する。

15. GitとPR/mergeの導線を追加する
    - Agentロール・権限プロファイルに従い、状態確認、PR作成・確認、最終的なmerge判断を扱う。

16. スマホ向けの部分操作と通知を追加する
    - TailscaleまたはMac・iPhone連携を比較し、状態監視・通知・質問への回答を優先する。
    - コマンド実行の承認命令とか出せるといいね
