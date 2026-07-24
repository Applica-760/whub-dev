# whub固有コンテキスト

whub CLIやデータモデルを変更する前に、必ず`whub knowledge query <対象>`で関連Knowledgeを確認すること。
運用フロー・Skillの判断基準・inbox/backlog/todoの関係を変更する前に、必ず`whub knowledge query <対象>`で関連Knowledgeを確認すること。
Knowledgeの追加・削除は`whub knowledge add`・`whub knowledge rm`を使い、`docs/knowledge.yaml`を直接編集しないこと。

# 概要

workspace-hubは`manifest.yaml`を単一定義源として、ローカルリポジトリ・自宅Linuxサーバ・大学スパコンのリソースを1つのディレクトリツリーに統合管理するCLIツール（`whub`）。

- ローカルリソースはsymlink、リモートリソースはsshfs mountで参照（実体は移動しない）
- CLIはPython（uv + Click + Pydantic）で実装。
- uv環境を使う
- テストは`uv run pytest`で実行する

## コマンド実行

- 承認を伴う複数コマンドは一つの実行リクエストにまとめてよい。論理コマンドごとに改行し、各コマンド内もオプションを適切に改行して可読にする。

## Operation release

- operation releaseの正本は`docs/operations/releace.md`とし、`whub release build --source <path>`、`verify`、`apply`を順に実行する。
- `build --source`にはcleanなwhub開発checkoutを明示し、release-idやsource pathを推測しない。

## Task運用

- 新規・未完了の個別作業はTask YAMLをSSOTとし、`wflow task`で操作する
- Taskの計画・承認・進捗・割り込み・完了は`task-planning` Skillに従う
- 完了済みMarkdown Taskは履歴として扱い、変更しない
