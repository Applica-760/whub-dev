# 要求定義: Task 121 Workflow state・Task文書の責務分離

- 状態: 草案
- 対象Task: `whub-dev:121`

## 目的

状態・計画・実行記録を一つのTask YAMLへ強制的に収める運用をやめる。Task固有の作業文脈は自由記述のMarkdownへ、Task間で整合性が必要な状態と関係はHub側のFlow serviceへ分離する。

## 合意済みの要求

### 責務と保存先

- Hub側はTaskごとにruntime YAMLを管理する。YAMLにはTask ID、lifecycle state、依存、割り込み、グラフ表示に必要な最小情報だけを保持する。
- TaskごとのMarkdownもHub直下で管理する。active YAMLと同じdirectory・basenameで、拡張子だけを`.md`にする。たとえば`20260805_1226_task-121.yaml`には`20260805_1226_task-121.md`を対応させる。
- Taskの完了後、Hub側のYAMLとMarkdownをProject repositoryのarchiveへ移す。basenameは維持する。完了済みTaskの長期的な作業文脈はrepository側に残す。
- Hub側のYAMLとMarkdownは、Taskの実行中はGitのbranch・worktreeに追従させない。YAMLだけがTask間の状態と関係の正本であり、MarkdownはTask内容の正本とする。

### Flow serviceとCLI

- 現在の`wflow`が持つ状態遷移・関係制約の資産は、`whub`内部のFlow serviceとして移行・維持する。
- `wflow`は公開CLIとして段階的に廃止し、利用者・Agent向けのTask操作は`whub task ...`へ統合する。
- この移行は一括削除ではない。互換期間を設け、CLI、Web、Skill、運用文書の移行が完了してから`wflow`公開CLIを削除する。
- Markdownの目的・計画・受け入れ条件をFlow serviceが解析して、状態遷移の可否を決めてはならない。

### 記録

- `whub task log`はAgentが承認なしで実行できる許可コマンドとする。
- log入力はCLIでJSON形式を強制する。`LogKind` enumを`fact`、`analysis`、`proposal`で定義し、入力JSONの唯一のキーとして使う。
- CLIは検証済みJSONを、定めた表示形式のMarkdownへ構造化して追記する。AgentはTask本文を自由に更新でき、ログだけは検索・表示に適した構造を保つ。
- CLIは記録時刻を補完し、`- <timestamp> | <LogKind> | <message>`としてMarkdown末尾へ追記する。JSON原文は別途保存しない。

### 人間とAgentの役割

- 通常のTask内容の更新はMarkdownへの直接記述とし、計画を細分化するたびにCLIを要求しない。
- すべての状態遷移は人間の許可を必要とする。actor属性は持たず、Agent authとCLI/Web adapterがこの境界を強制する。
- Taskを完了宣言する前に、Agentは実装・検証結果を確認し、Task Markdownへ根拠を記録する。確認不能な完了条件がある場合は、Agentがユーザーへ確認を求める。この行動規約は後続でTask planning Skillへ反映する。

## 検討テーマ 1: 現行Task YAMLの保存先

この表を、Taskごとの最小runtime YAML schemaとTask Markdownの責務のたたき台とする。Flow serviceはMarkdownを状態遷移のguardとして読まない。

| 現行の項目 | 判断 | 移行先・扱い |
|---|---|---|
| `schema_version` | 残す | Hub側runtime YAML |
| Task ID | 残す | Hub側runtime YAML |
| Workflow ID | 残す | Hub側runtime YAML。現行は組込みTask Workflowに固定だが、Flow serviceのinstanceとして明示する |
| lifecycle `state` | 残す | Hub側runtime YAML |
| `depends_on` | 残す | Hub側runtime YAML。開始可否のguardに使う |
| `interruption_task_id` / `interruption_source_task_id` | 残す | Hub側runtime YAML。親子関係とpause/resumeのguardに使う |
| `interruption_reason` | 移す | Task Markdownの構造化ログ。関係の整合性には使わない |
| `title` | 移す | Task Markdown。グラフはTask IDを必須表示とし、titleは読める場合だけ補助表示する |
| `objective` / `approach` | 移す | Task Markdownの自由記述 |
| Phase・Step・各Stepのstate・skip reason・論理削除 | 消す | Markdownの計画・チェックリスト・作業メモへ置き換え、Flow serviceでは解釈しない |
| acceptance criteria・acceptance result・evidence | 移す | Task Markdown。完了前にAgentが確認・記録するが、Flow serviceのguardにはしない |
| Phase log | 置換 | `whub task log` がJSONを検証し、Task Markdownへ構造化追記する |
| plan approval・change request履歴 | 移す | Task Markdownの判断記録。runtime stateには保持しない |
| cancellation reason | 移す | Task Markdownの構造化ログ。stateはruntime YAMLへ残す |
| completion result | 移す | Task Markdownの最終結果・検証記録。stateはruntime YAMLへ残す |

### この判断で廃止するguard

- planの存在または承認を、開始・割り込み・resume・completeの前提にすること。
- Stepの完了、acceptance result、Task resultを、completeの前提にすること。
- Task Markdownの内容をFlow serviceが解析して遷移可否を決めること。

## 検討テーマ 2: lifecycleとTask間関係

運用ルールは現状維持とする。Flow serviceは既存の`draft`、`in_progress`、`paused`、`completed`、`cancelled`と、その遷移を維持する。

- 依存先が`completed`でないTaskは開始できない。
- 割り込みは`in_progress`の親から開始し、親を`paused`にする。子Taskには依存の充足、同一親への有効な子Taskが一つだけであること、親子参照の整合性を要求する。
- 割り込み理由はoperation inputとして必須のままにし、Task Markdownの構造化ログへ記録する。
- resumeは、親が`paused`であり、対応する子Taskが`completed`または`cancelled`の場合だけ許可する。
- 完了・cancelは既存のstate遷移の意味を維持する。ただしplan、Step、acceptance、Task Markdownの内容はguardにしない。

## 検討テーマ 3: 構造化ログ

`LogKind`を`fact`、`analysis`、`proposal`で定義する。`whub task log`の入力は、その値を唯一のキーとするJSON objectだけとする。

```json
{"fact":"確認した事実"}
```

- JSON objectはキーを一つだけ持つ。そのキーは`LogKind`、値は空でない文字列とする。未知のキー、複数のキー、空文字列は受け付けない。
- CLIが記録時刻を補完し、Task Markdown末尾へ活動ログを追記する。
- JSON原文を別ファイルやYAMLへ保存しない。属性の追加は必要になった時点でschemaを拡張する。

## 検討テーマ 4: 完了とarchive

- 既存のTask完了タイミングは維持する。archive時に、Hub側のactive YAMLと対応するMarkdownを、Project repositoryの`docs/tasks/done/`へ同じbasenameのまま移す。
- YAMLとMarkdownの両方を移せた場合だけarchive成功とする。失敗時は片方だけをarchiveに残さず、active側のペアを維持または復旧する。
- Taskの読込はactiveを優先し、archiveは履歴として読む。activeとarchiveに同じTask IDが同時に存在する場合は不整合として拒否する。

## 後続で決めること

- `whub task`の公開コマンド構成、互換CLIの提供期間。
- Task planning Skillにおける完了前検証・ユーザー確認の具体的な手順。

## 要求メモ（原文）

<!-- 順序・重複・書式を気にせず、この下に要求を記入してください。 -->

State管理が形骸化している
計画詳細も形骸化している、自由記述のmdにしたい
Yamlはタスク間依存やグラフビュー、割り込みの表現に終始する
目的や方針をmdで自由に書き足せるのがいい
あまりCLIでガチガチにしすぎない。基本はmdにしてAgentに自由に書かせて、割り込みとかの時だけCLIで人間の承認をつける
今はPhaseを挿入するだけでもCLI許諾が入るので面倒
LogのJson形式は維持するあくまで案だが、観測事実、考察、方針案などの規程属性を決めて、それに基づいたログが書けるようにする
wflow コマンド系は廃止して、whubに統合したい
