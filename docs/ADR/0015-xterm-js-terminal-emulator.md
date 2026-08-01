# ADR-0015: ブラウザ端末にxterm.jsを採用する

- **Status:** Accepted
- **Date:** 2026-08-01

## Context

whub appは、複数のCoding Agentを監督し、必要な判断と入力を返す主要な対話面へ段階的に移行する。Agent sessionはブラウザの切断やWeb appの再起動後も継続する必要があるため、実体をtmux sessionとして保持する。

ブラウザから既存tmux sessionを操作するには、端末エスケープシーケンス、リサイズ、マウス操作、日本語入力を扱える端末エミュレータと、認証・入力権制御を持つ接続経路が必要である。

## Decision

ブラウザ端末の表示と入力にはxterm.jsを採用する。

- xterm.jsはブラウザ側の端末エミュレータだけを担う。
- whub Web appは認証済みWebSocket接続を介してxterm.jsとtmux sessionを中継する。
- tmux sessionをAgent実行の永続実体とし、ブラウザ接続ごとにshellやPTYを新規作成しない。
- sessionごとの入力権は一接続に限定し、その認可と移譲はwhub側で扱う。

## Rationale

- tmux、対話型CLI、CJKを含む端末アプリケーションに必要な互換性を持つ。
- `fit`、検索、リンク検出などの拡張により、監督画面へ段階的に必要な操作性を追加できる。
- 現行Web appのTypeScript/Vite frontendとFastAPI backendへ、端末表示と接続制御を分離して組み込める。
- tmuxを実体に固定するため、再接続とAgent実行の継続をWeb UIのライフサイクルから分離できる。

## Alternatives considered

### ブラウザ接続ごとにPTYとshellを起動する

実装は単純だが、ブラウザを閉じると対話と実行文脈を失う。`1 Task = 1 worktree = 1 Agent session`とtmuxによる再接続の要件に合わないため採用しない。

### 汎用のWeb terminalサーバーを独立して導入する

短期の疎通確認は容易になるが、whubの認証、Task・worktree・sessionの対応、単一入力権を別系統で管理することになる。control planeとの統合を優先し、採用しない。

### xterm.jsを接続基盤として扱う

xterm.jsは端末エミュレータであり、PTY、tmux、認証、WebSocketのサーバー側制御を提供しない。接続ブリッジはwhub側で実装する。

## Consequences

- Web terminal実装は、tmux接続ブリッジとxterm.js UIの二層に分ける。
- WebSocketの認証、session識別、入力権、resize、切断後の再接続を接続ブリッジの受け入れ条件とする。
- xterm.jsの導入は、監督画面の状態・依頼文・通知を置き換えず、それらと組み合わせて利用する。
