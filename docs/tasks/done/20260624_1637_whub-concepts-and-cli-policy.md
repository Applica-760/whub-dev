# 目的・前提・方針案

## 目的
whubの用語定義とCLI実装ポリシーを明文化し、以後のTarget/Routerとroadmap実装の前提を固定する。

## 前提
- workspace-hubはprojectではあるが、mount/link対象ではないためresourceではない
- 現状はwhub自身をstatus/cd/todo/roadmapの対象として自然に扱えない
- CLIと頒布SkillでProjects / Resources / Todo(tasks) / status / roadmapなどの語が混ざりやすい
- Click関数直下はlocal/remoteを意識しない読みやすい構成を目指す
- Target/Routerは一般操作だけを担い、コマンド固有ロジックは各コマンド側に残す
- manifestに`projects`を追加し、`project`と`resource`を分離する方向で整理する
- `project`の必須フィールドは`name`だけにし、大学課題や事務手続きのような物理`resource`を持たない活動も扱えるようにする
- `workspace-hub`は暗黙ではなく明示的な`project`として定義する
- 1つの`project`に紐づく`resource`は最大1つとし、複数`resource`の束ね上げは扱わない
- `resource`側は`workspace_path`など既存の具体的なフィールド名を維持し、曖昧な`path`へ寄せない
- `cd <project>`は紐づく`resource`がない場合、移動先なしを英語エラーで通知する
- `whub cd whub`は例外扱いせず、`resource`なし`project`として移動先なしを英語エラーで通知する

## 方針案
- 用語定義ドキュメントとCLI実装ポリシーを同じ文書にまとめる
- 既存実装を読み、現在の用語・責務とズレている箇所を記録する
- この文書を作ってからTarget/Router、`whub roadmap`の順に進める
- `docs/whub-concepts.md`をwhub CLI変更時の参照必須ドキュメントとして扱う
- 既存コマンドのproject/resource新スキーマ対応は破壊的変更として後続タスク化する

# 計画

## Phase 1: 現状整理
- [x] 既存CLI、manifest、tasks、ADRで使われている用語を確認する
- [x] whub自身、project、resource、todo、roadmap、statusの関係を整理する

## Phase 2: ドキュメント作成
- [x] 用語定義を短く書く
- [x] CLI実装ポリシーをClick層、コマンド固有処理、Target/Router、remote.pyに分けて書く
- [x] Target/Routerとroadmap実装の前提条件を明記する
- [x] manifestの`projects`追加方針とフィールド命名規則を記録する
- [x] `project`と`resource`の0/1対1関係を記録する
- [x] `docs/whub-concepts.md`をAI/Agentが参照する導線を決める

## Phase 3: 反映確認
- [x] longterm-todo、既存task、ADRとの矛盾を確認する
- [x] 必要なら後続タスクの前提を更新する

## Phase 4: 後続改修の整理
- [x] manifestスキーマ変更タスクを切る
- [x] `todo` / `roadmap`を`project`参照へ移行するタスクを切る
- [x] `status` / `cd` / `boot`など既存コマンドの新フィールド対応を洗い出す
- [x] 既存データ移行と破壊的変更の検証条件を決める

# 実行ログ

# 結果
`docs/whub-concepts.md`を正本として用語とCLI実装ポリシーを整理し、manifest v2移行タスクへ反映した。
