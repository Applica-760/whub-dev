# 目的・前提・方針案

## 目的
manifestに`projects`を追加し、`project`と`resource`を分離したうえで既存CLIの参照・命名を正す。

## 前提
- 正本は`docs/whub-concepts.md`
- `project`は活動単位で、必須フィールドは`name`のみ
- `workspace-hub`は明示的な`project`だが、`resource`ではない
- 1つの`project`に紐づく`resource`は最大1つ
- `resource`は`project`直下の任意フィールドとして定義する
- `resource`側の`workspace_path`、`source`、remote `path`などの具体名は維持する
- 現行実装は`projects`なし、`resources.symlinks` / `resources.remotes`中心のスキーマ
- `todo.project`は名前上projectだが、現行実装ではresource名と照合している
- `cd`は現行実装ではresource引数だが、方針上は`project`または`resource`へ移動する
- `status`と`boot`は引き続き`resource`操作を主責務とする

## 方針案
- manifest versionは`"2"`へ更新する
- manifest案は`projects[].resource`に`type: symlink | remote`のresourceを任意で持たせる
- 初期移行では既存`resource.name`と同名の`project`を作り、`workspace-hub`をresourceなしprojectとして追加する
- `esn-lab`と`esn-lab-run`のような複数resource候補は、最大1resource/project方針に従い別projectとして扱う
- `todo`はproject名を保存・補完・検証し、既存resource名保存値はproject名へ読み替える
- `cd`はproject名を受け取り、紐づくresourceへ移動する
- `project`に紐づく`resource`がない場合は移動先なしを英語エラーで通知する
- `boot`はresourceに対する操作だが、workspace-hub自身への配布だけ例外として維持する
- Target/Router導入は別タスクとし、本タスクではスキーマ・参照・命名の整合に集中する

## スキーマ案

```yaml
version: "2"

projects:
  - name: workspace-hub

  - name: mind
    resource:
      type: symlink
      workspace_path: mind
      source: /path/to/mind
      boot: true

  - name: esn-lab
    resource:
      type: remote
      host: home-server
      path: /remote/path
      boot: true
```

# 計画

## Phase 1: 仕様確定
- [x] `docs/whub-concepts.md`の`project`/`resource`関係表記を確認し、最大1resource/projectに揃える
- [x] manifest versionは`"2"`へ更新する
- [x] `cd`はproject名を受け取りresource直指定互換は残さない
- [x] `workspace-hub`の`boot`配布は例外として維持する

## Phase 2: manifestモデル移行
- [x] `Project`モデルと`Manifest.projects`を追加する
- [x] `Project.resource`へ`type`で判別するsymlink/remote resourceを任意で持たせる
- [x] 既存コマンド向けの互換列挙APIは残さず破壊的に移行する
- [x] `project_names`を追加し、旧`resource_names`を削除する

## Phase 3: データ移行
- [x] `.whub/manifest.yaml`をversion 2の`projects[].resource`形式へ移行する
- [x] `workspace-hub`をresourceなしprojectとして追加する
- [x] `.whub/todos.yaml`の既存project値を必要ならresource名からproject名へ移行する
- [x] READMEとADR-0004のスキーマ例を現行化する

## Phase 4: CLI参照・命名修正
- [x] Manifestモデルにv2前提の最小APIを追加する
- [x] `link`を`projects[].resource`参照へ変更する
- [x] `todo`の補完・検証をresource名からproject名へ変更する
- [x] `cd`をproject解決に変更し、resourceなしprojectの挙動を実装する
- [x] `status`はresourceヘルスチェックとして命名・表示だけ確認する
- [x] `boot`のworkspace-hub扱いを決定方針に合わせて整理する

## Phase 5: サンドボックス確認
- [x] v2 manifestを読み込む
- [x] `cd` / `todo`をdemo manifestで確認する
- [x] `link` / `status` / `boot`のv2参照をAST parseとdemo抽出で確認する

# 実行ログ

### 試行 1: サブエージェントによる既存検討要点の抽出
- 実施内容: docs、manifest実装、todo/cd/status/boot実装からスキーマ案・影響範囲・移行リスクを抽出
- 結果: `projects`追加、resourceの`project`参照、todo/cdのresource名依存、version/互換判断が主要論点
- 判断: 続行

### 試行 2: manifestモデルをversion 2へ破壊的に移行
- 実施内容: 互換APIは残さず、`projects[].resource`構造へモデル定義を更新する
- 結果: `uv run python -m unittest src.whub.tests.test_manifest` 成功
- 判断: 続行

### 試行 3: manifest YAMLをversion 2へ移行
- 実施内容: `.whub/manifest.yaml`を`projects[].resource`形式へ変換し、READMEとADR-0004を更新
- 結果: `uv run python -c 'from whub.models import load_manifest; ...'` 成功、todoはproject値なしのため移行不要
- 判断: 続行

### 試行 4: Manifestのv2向け最小APIを追加
- 実施内容: `workspace_root`、`resolve_project`を追加し、先回りの列挙APIは削除
- 結果: `uv run python -m unittest src.whub.tests.test_manifest` 成功
- 判断: 続行

### 試行 5: resource操作系コマンドをv2参照へ移行
- 実施内容: `link`、`status`、`boot`を`project.resource`参照へ変更
- 結果: demo manifestでAST parse、link/status/boot対象抽出、resourceなしproject解決を確認
- 判断: 続行

### 試行 6: todoコマンドをproject参照へ移行
- 実施内容: `resource_names`と`all_resources`参照を`project_names`と`resolve_project`へ変更
- 結果: demo manifestでAST parse、project解決、resourceなしproject許可を確認
- 判断: 続行

### 試行 7: cdコマンドをproject解決へ移行
- 実施内容: `resource_names`と`all_resources`参照を`project_names`と`resolve_project`へ変更
- 結果: demo manifestでAST parse、symlink/remote/resourceなしproject/missing project解決を確認
- 判断: 続行

### 試行 8: サンドボックスでPhase 5検証
- 実施内容: bytecode生成なしで既存テスト、AST parse、demo manifestによるcd/todo確認を実行
- 結果: manifest/remote/boot markerテスト成功、cd/todo demo成功、全件discoverはtempfile不可でboot filesystem系が実行不能
- 判断: 続行

# 結果
manifestをversion 2の`projects[].resource`構造へ移行し、主要CLI参照をproject/resourceモデルへ更新した。テスト整備は後続のTarget/Routerタスクで扱う。
