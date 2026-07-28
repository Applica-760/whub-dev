# Agent workspace requirements

## Purpose

whub appを、複数のCoding Agentを並列に動かし、人間が必要な判断だけを返すための主要インターフェースへ段階的に移行する。

## Required experience

- ブラウザからターミナルを操作できる。
- CodexやClaude CodeなどのAgentと継続して対話できる。
- 複数Agentを並列起動し、各Agentが考え中か、質問への回答待ちか、権限承認待ちかを一望できる。
- 各Agentが何を依頼され、どこまで進んだかを、ログを遡らずに把握できる。
- Agentの状態・依頼文・summary・通知によって、人間が対応すべきAgentを探しに行かなくてよい。
- hub内のfile explorerを利用できる。初期段階では閲覧専用とし、編集は後から追加する。
- PR作成・確認・merge判断を行える。

## Parallel execution

- `1 Task = 1 worktree = 1 Agent session` を基本単位とする。
- `whub worktree` により、git worktreeの実行と対応するproject symlinkの作成を決定論的に行う。
- ブラウザを閉じてもAgent sessionは維持され、あとから再接続できる。
- tmuxをsessionの永続化に利用する。

## Agent authority

- Agentごとに用途別の権限プロファイルを持たせる。
- 限定された書き込み権限のAgentが実装・PR作成を担えるようにする。
- ファイル削除、build、mergeなど強い操作は、あなたまたは権限のない対話Agentによる明示的な判断・承認を経て実行する。
- 権限プロファイルの具体的な種類と詳細な承認方式は後続で決める。

## Environments and rollout

- 主な利用環境はMacとする。
- スマホではMacと完全に同等の操作を目指さず、状態確認、通知、質問への回答などの部分操作を優先する。
- スマホ接続はTailscaleまたはMac・iPhone連携を候補とする。
- VS Codeを当面維持し、機能が整った範囲からwhub appへ段階的に移行する。
- 複数人利用、外部公開、完全自律実行は対象外とする。
