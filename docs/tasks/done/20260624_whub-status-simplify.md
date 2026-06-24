# 目的・前提・方針案

## 目的
`whub status` をヘルスチェック専用に簡素化し、priority/statusテキストの責務を `whub todo` に移譲する。

## 背景
- statusのpriority・statusテキストはtodoのproject+priority+titleと実用上重複している
- statusはリンク・接続状態・git差分の確認に特化し、タスク管理・優先度把握はtodoに任せる（longterm-todo.md 19行目の構想）

## 想定スコープ
- `whub status` から `-e`（statusテキスト設定）・`-p`（priority設定）オプションを削除
- `state.yaml` / `State` / `ResourceState` モデルの廃止
- statusの表示からpriority列・statusテキスト列を除去
- READMEとlongterm-todoの関連記述を更新

## 未決事項
- なし

# 計画

# 実行ログ

# 結果
