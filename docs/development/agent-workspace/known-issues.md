# Agent workspace known issues

Agent Harnessの現状で確認している課題を、今後の設計・実装の入力として集約する。

## Agent execution context

- sandbox内で割り当てられたworktreeの作業者であることを、Agentが十分に理解できない。
- Hubのコンテキストファイルをコピーするだけでは、継続作業に必要な文脈を引き継げない。
- worktree内で完結する変更でも親Projectを編集しようとして、権限拒否後に作業の整合性を見失うことがある。
- `wflow task` 実行後にworktree内のTask YAMLを見て、反映されていないと誤認することがある。本元のTask YAMLがHub側のSSOTである認識が不足している。
- テスト実行系コマンドの許可がexact matchに限定され、実行時の柔軟性を欠く。prefix許可への見直しが必要である。

## Terminal interaction

- Shift+Enterが利用できず、Option+Enterを使う必要がある。
- 色分けが少なく、状態と出力の視認性が低い。
- 実行リクエストのコマンド表示が見にくい。

## Direction

- Agentの実行コンテキストを、worktree、Task SSOT、権限境界、許可済み操作として明示する。
- xterm.jsを使うWeb UIでtmux sessionを操作・監督し、入力操作と視認性を改善する。

## Roadmap to Web UI

1. Task、worktree、tmux sessionの一意な対応と、Agentの起動・再接続・終了を確定する。
2. Agent adapterとlifecycle hooksから、状態・質問・権限要求をcontrol planeへ正規化して保存する。
3. tmux接続ブリッジを実装する。認証、単一の入力権、WebSocket、resize、切断後の再接続を扱う。
4. xterm.jsの単体画面で、既存tmux sessionへの入出力を検証する。
5. whub Web appから、Task、worktree、依頼文、状態に対応する端末を開けるようにする。
6. 監督画面で`input_requested`と`approval_requested`を優先表示する。
7. スマホには閲覧、質問への回答、通知を限定して追加する。
