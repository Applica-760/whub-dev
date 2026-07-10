# 実行仕様書: whub app S2a — サービス層抽出

## 目的
- todo/backlogの業務処理をCLIコマンドからClick非依存の`services/`層へ抽出し、CLIとWebの双方から呼べる構成にする

## 背景・前提
- 全体ロードマップと層分離方針は`docs/tasks/20260708_2108_existing-features-html-view.md`を正とする
- S1（server基盤）は実装済み。S2b（リソースAPI）が本仕様のservicesを呼ぶ前提の準備リファクタである
- CLI振る舞い不変の純粋リファクタであり、新機能を含まない
- 既存平置きモジュール（`paths.py`・`remote.py`等）の`core/`移設は別タスク（`docs/tasks/20260710_1319_core-package-restructure.md`）で扱い、本仕様では行わない

## 対象範囲
- `src/whub/services/`（新規: `__init__.py`・`errors.py`・`todo.py`・`backlog.py`）
- `src/whub/commands/todo.py`（痩身化）
- `src/whub/commands/backlog.py`（痩身化）
- `docs/whub-concepts.md`（責務境界の更新）
- `src/whub/tests/`（services単体テスト追加）

## 非対象範囲
- 新規APIエンドポイント（S2b）
- `webapp/`・`models/`の変更（todoのload/saveは現行どおり`models/todo.py`に残す）
- 既存平置きモジュールの移設・改名

## 変更要件
- `services/errors.py`
    - `ServiceError(Exception)`: 業務エラーの基底（不正操作・remote失敗等）
    - `NotFoundError(ServiceError)`: 対象不在
- `services/todo.py`（`commands/todo.py`から移設）
    - `list_pending() -> list[Todo]`: 未完了一覧。due昇順（無期限は末尾）→priority→idの現行ソートを適用して返す
    - `list_completed() -> list[Todo]`: 完了一覧。done_at→idの現行ソートを適用して返す
    - `add_todo(manifest, title, project, priority, due_date) -> Todo`: project存在検証（不明は`ServiceError`）・id採番（既存最大+1）・保存。due_dateは`date`型または未指定
    - `complete_todo(todo_id) -> Todo`: 不在は`NotFoundError`、既doneは`ServiceError`。done/done_atを設定し保存
    - `remove_todo(todo_id) -> Todo`: 不在は`NotFoundError`。削除して保存
- `services/backlog.py`（`commands/backlog.py`から移設）
    - マーカー定数とマーカー検証込みの挿入処理を移設する
    - `append_backlog(manifest, project, memo) -> None`: project→resource解決とtarget機構によるlocal/remote書込。remote前提チェック（パス存在・ファイル種別）は現行を維持。失敗は`ServiceError`
- `services/`は`click`への依存（import・echo・ClickException）を一切持たない
- `commands/todo.py`: 引数解釈（MMDD形式のdue解釈を含む）・テーブル表示・例外変換（`ServiceError`→UsageError/ClickException）のみ担う
- `commands/backlog.py`: 引数整形・表示・例外変換のみ担う
- `docs/whub-concepts.md`: 「ドメイン処理は各コマンド側に置く」を、services層前提の責務境界（models=データ・検証・load/save、services=操作、commands/webapp=アダプタ）へ更新する
- CLIの出力文言・終了挙動は変更しない

## 実装方針
- ソート順・採番・状態遷移の規則は現行実装の振る舞いを正とし、変更しない
- backlogのremote書込は`remote.py`の既存低レイヤーをそのまま使う
- CLI固有の入力形式解釈（MMDD等）と表示（テーブル描画・絵文字）はcommandsに残す。この線引きが以後のアダプタ/サービスの境界規範になる
- テストに必要なdev依存の追加は実装者の裁量で可

## 受け入れ基準
- [ ] `uv run pytest`が全件通る
- [ ] `whub todo`系・`whub backlog`の出力・挙動がリファクタ前と一致する
- [ ] `services/`が`click`をimportしていない
- [ ] `commands/todo.py`・`commands/backlog.py`に採番・状態遷移・ファイル書込ロジックが残っていない
- [ ] services単体テスト（採番・done切替・削除・マーカー挿入・`NotFoundError`/`ServiceError`）が追加されている
- [ ] `docs/whub-concepts.md`の責務境界が更新されている

## 検証条件
- 自動: `uv run pytest`。services単体テストは一時ディレクトリをデータ置き場に注入してファイル実体を検証する
- 手動: `whub todo`・`whub todo add`・`whub todo done`・`whub backlog`をリファクタ前後で実行し出力を突合する

## リスク・注意点
- remote backlogのSSH経路は自動テストが困難。コマンド組み立ての単体テストに留め、実SSHは手動確認とする
- 出力文言の微差は既存テストで捕捉できない場合がある。前後の手動突合で補う

## 不明点・確認事項
- なし（ソートの層・`rm`移設・例外粒度は相談済み決定事項）
