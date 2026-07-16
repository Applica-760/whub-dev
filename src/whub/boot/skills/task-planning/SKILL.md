---
name: task-planning
description: 下記に従いタスクの計画・記録ドキュメントを作成する。
---
# タスク計画Skill

## 基本ルール
- ファイルパス規約: `docs/tasks/YYYYMMDD_HHmm_<topic>.yaml`
- 新規・未完了のTaskはYAMLで管理し、完了済みMarkdownは履歴として変更しない
- Taskの構造・状態・実行事実はYAMLをSSOTとする
- 実行ログは各Phaseの`log`に記録する
- 原則 1 Task = 1 commit

## 手順
1. Skill呼び出し時に数字が付く場合は、`wflow task check <番号>`と`wflow task show <番号>`で対応する既存Taskを読む
2. 次に基づいて計画を立案
  - **目的・前提・方針案**
  - コードベースの実装
  - 指示に応じたWebSearch
3. 次をチャットに出力
  - 1.の計画概要
  - 情報不足、不明点
  - 意思決定が必要な点
4. Phaseに関わらず、情報不足・不明点・意思決定が必要な点を検知したら、影響と選択肢を添えてユーザーへ質問し、解決まで該当作業を進めない
5. ユーザー承認後、Task YAMLへPhase・Stepを記録し、`wflow task check TASK`で検証してから`wflow task transition TASK approve_plan --actor user`で開始する
6. Stepの完了・skipは`wflow task done`・`skip --reason`で記録し、`--log`は複数回指定できる
7. 想定外の事象、バグ、再利用すべき発見に遭遇したら、該当Stepの記録時に`--log`で該当Phaseの`log`へ追記する
8. 計画を変更する場合は`request_plan_change`で理由を記録して再承認を得る
9. 受け入れ条件があれば`wflow task accept`で結果を記録し、全Step完了後に`complete_task`で完了する
10. 完了したTask YAMLを`docs/tasks/done`へ移動する
