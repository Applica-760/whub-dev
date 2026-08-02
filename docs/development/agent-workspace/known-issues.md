# Agent workspace known issues

Agent Harnessの現状で確認している課題を、今後の設計・実装の入力として集約する。

## Agent execution context

- sandbox内で割り当てられたworktreeの作業者であることを、Agentが十分に理解できない。
- Hubのコンテキストファイルをコピーするだけでは、継続作業に必要な文脈を引き継げない。
- worktree内で完結する変更でも親Projectを編集しようとして、権限拒否後に作業の整合性を見失うことがある。
- `wflow task` 実行後にworktree内のTask YAMLを見て、反映されていないと誤認することがある。本元のTask YAMLがHub側のSSOTである認識が不足している。
- テスト実行系コマンドの許可がexact matchに限定され、実行時の柔軟性を欠く。prefix許可への見直しが必要である。

## Release workflow

- `whub release`は、変更がmerge済みの親repoだけから実行できるよう制約し、Task worktreeや未merge branchからの実行を拒否する。
- release build・verify・apply・適用後の動作確認を、一貫した検証条件を保ったまま自動化する。

## Task development workflow

- PR作成にAgentの再起動やworktreeの切断が伴うため、小さな論理変更ごとにPRを分割する運用コストが高く、一度のPRが大きくなりやすい。
- Agentとworktreeを維持したままdraft PRを作成・更新し、test・Task log・commit・push・PR更新をcheckpointとして自動化できるようにする。
- merge後の次Task作成・worktree作成・Agent再接続を一操作にまとめ、レビュー前後の手動引継ぎを減らす。

## Terminal interaction

- Shift+Enterが利用できず、Option+Enterを使う必要がある。
- 色分けが少なく、状態と出力の視認性が低い。
- 実行リクエストのコマンド表示が見にくい。

### Deferred UX

- Codex・Claude Code向けに、複数行のpromptをtextareaへ保持し、Enterで送信、Shift+Enter・Option+Enterで改行できるcomposerを追加する。Terminalの表示改善とは入力契約が異なるため、後続Taskで扱う。
- URLとANSI paletteを超えて、引用符・`#`・code spanなどを意味的に着色する場合は、PTY出力を直接装飾せず、Terminalとは別のtranscript／Markdown表示として後続Taskで設計する。
- worktreeごとの`git diff`をWeb app内の専用タブで確認できるようにする。PR作成前にコードレビューと修正を完結させ、Web appと外部サイトを往復する負担を減らす。
- Codexがコマンド実行の承認を求める直前に発火する`PermissionRequest` Hookを使い、`session_id`・`cwd`・`turn_id`・tool情報をwhubのcontrol planeへ送る。PTYの特定文字列には依存せず、セッション一覧の承認待ちbadge、Terminalの強調枠、固定banner、対象Terminalへの導線として表示する。[Codex Hooks](https://learn.chatgpt.com/docs/hooks#permissionrequest)に入力情報と通常の承認promptを継続できる契約が記載されている。
- 承認待ち中にWeb appのtabが非表示ならbrowser notificationを送り、判断待ちを見落とさないようにする。実行後は`PostToolUse`で表示を解除し、拒否・放置時に完了eventが得られない場合は有効期限で解除する。厳密な状態同期とWeb app内での承認操作は、`item/permissions/requestApproval`を提供する[Codex App Server](https://learn.chatgpt.com/docs/app-server#api-overview)との統合を後続検討とする。

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
