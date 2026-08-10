# Agent workspace requirements

## Purpose

whub appを、複数のCoding Agentを並列に動かし、人間が必要な判断だけを返すための主要インターフェースへ段階的に移行する。

最初の対象は、単一利用者がローカルのProjectでCodexと複数のworktreeへ安全に開発Taskを委譲することとする。Claude Code対応は後続の拡張とし、外部公開、共同編集、完全自律実行は対象にしない。

## Initial use cases

- 小規模なリファクタリングをAgentへ委譲する。

## Safety and autonomy requirements

- Codex sandboxを安全境界とする。対応worktreeをworkspace rootとし、worktree外の操作はCodexの承認要求へ委ねる。
- worktree内のファイル操作と通常のcommandは自律実行を許容する。削除とGit操作をMVPで一律に禁止しない。
- command allowlistはCodex rulesへ変換する。sandbox外でCodexまたはrulesが承認を要求する操作は、利用者が確認して許可または拒否する。
- Codex processのsandbox network accessは無効にする。Web検索はextension tool経由で行う。
- Agentが自律的に連続実行できる上限を設定できるようにする。上限に達したら停止し、利用者の判断を求める。
- 承認が必要な操作は、可能な限りまとめて利用者へ提示する。
- 複数のtmux sessionを一画面で監督し、対応するworktreeの作業内容を実行中から確認できることを理想とする。強い安全境界に必要な場合だけ、隔離した作業結果を後から反映する方式を検討する。

## Required experience

- ブラウザからターミナルを操作できる。
- Codexと継続して対話できる。
- 複数Agentを並列起動し、各Agentが考え中か、質問への回答待ちか、権限承認待ちかを一望できる。
- 各Agentが何を依頼され、どこまで進んだかを、ログを遡らずに把握できる。
- Agentの状態・依頼文・summary・通知によって、人間が対応すべきAgentを探しに行かなくてよい。
- hub内のfile explorerを利用できる。初期段階では閲覧専用とし、編集は後から追加する。
- PR作成・確認・merge判断を行える。

## Parallel execution

- `1 Task = 1 worktree = 1 Agent session` を基本単位とする。
- git worktreeをTask branchと規約pathで決定論的に操作する。
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
