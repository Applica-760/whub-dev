---
name: task-planning
description: 下記に従いタスクの計画・記録ドキュメントを作成する。
---
# タスク計画Skill

## 基本ルール
- 新規・未完了のTaskはYAMLで管理し、完了済みMarkdownは履歴として変更しない
- Taskの構造・状態・実行事実はYAMLをSSOTとする
- 実行ログは各Phaseの`log`に記録する
- 新規Taskは手書きの雛形を使わず、`wflow task init`で生成する
- 原則 1 Task = 1 logical change。Task内に独立した論理的変更単位が複数ある場合は、検証済みPhase成果ごとにcommitしてよい
- Phase完了時、その成果が独立して検証・説明・revert可能な論理的変更単位であり、検証が成功している場合はcommitする
- commitメッセージは`<type>: <summary> (<TASK-TTT:PPP>)`とし、
  - `type`は`feat`、`fix`、`refactor`、`chore`など、一般に使われるものから選ぶ
  - `summary`は変更概要
  - `TTT`はタスクID、`PPP`はPhaseID

## 手順
1. Skill呼び出し時に数字が付く場合は、`wflow task check <番号>`と`wflow task show <番号>`で対応する既存Taskを読む
2. 新規Taskは`wflow task init "タイトル" "目的" --approach "方針"`でdraftを作成し、`wflow task plan insert`でPhaseとStepを追加する
3. 次に基づいて計画を立案
  - **目的・前提・方針案**
  - コードベースの実装
  - 指示に応じたWebSearch
4. 次をチャットに出力
  - 1.の計画概要
  - 情報不足、不明点
  - 意思決定が必要な点
5. Phaseに関わらず、情報不足・不明点・意思決定が必要な点を検知したら、影響と選択肢を添えてユーザーへ質問し、解決まで該当作業を進めない
6. ユーザー承認後、draft Taskへ`wflow task plan insert`でPhase・Stepを記録し、`wflow task check TASK`で検証してから`wflow task transition TASK approve_plan --actor user`で開始する
7. 計画を変更する場合は、`wflow task transition TASK request_plan_change --actor agent --reason "…"`でdraftへ戻す。`wflow task plan delete`で不要なPhaseまたはStepを論理削除し、`plan insert`で必要なStepを追加して、再承認を得る
8. Stepの完了・skipは`wflow task done`・`skip --reason`で記録する。進捗を変えない記録は`wflow task log TASK PPP --log "…"`でPhaseの`log`へ追記し、Phase完了時の`done`・`skip`では`--log`を指定する
9. 割り込みは`wflow task interrupt PARENT CHILD --reason "…"`で親Taskをpausedにして子Taskを開始する。子Taskがcompletedまたはcancelledになった後、`wflow task resume PARENT`で親Taskを明示的に再開する
10. 受け入れ条件があれば`wflow task accept`で結果を記録し、全Step完了後に`wflow task complete TASK --result "…"`で完了と`docs/tasks/done`へのアーカイブを一操作として行う。完了後の手動移動・移動後checkは通常手順に含めない
