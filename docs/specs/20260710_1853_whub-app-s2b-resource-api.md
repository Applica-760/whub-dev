# 実行仕様書: whub app S2b — リソースAPI

## 目的
- S2a/S1.5のservicesを呼ぶtodo/projects/backlog/inboxのJSON APIをwebappへ追加し、S3以降のフロントが使うAPI契約を確定する

## 背景・前提
- 設計方針は`docs/tasks/20260708_2108_existing-features-html-view.md`の「S2bのAPI設計方針（2026-07-10 決定）」を正とする
- S1（server基盤）・S2a（services抽出）・S1.5（inbox service）は実装済み
- 認証・CORSなし（127.0.0.1限定）。競合制御はlast-write-wins
- エラー境界は`docs/tasks/done/20260710_1411_service-error-boundary.md`（TargetError純化）の前例に倣う

## 対象範囲
- `src/whub/webapp/routers/`（新規: `__init__.py`・`todos.py`・`projects.py`・`backlog.py`・`inbox.py`）
- `src/whub/webapp/server.py`（ルータ・例外ハンドラ登録）
- `src/whub/models/manifest.py`（`ManifestError`化）
- `src/whub/commands/__init__.py`（`get_manifest`の例外変換）
- `src/whub/services/backlog.py`（読取関数の追加）
- `src/whub/tests/`（webapp APIテスト・境界変更テスト）

## 非対象範囲
- フロントエンド一式（S3/S4）
- todoのundone・タイトル編集等、servicesに無い操作
- inboxの読取・一覧API（投函口の責務外、S1.5準拠）
- FOCUSビュー・discourse連携（S5）

## 変更要件
- `models/manifest.py`
    - 純粋例外`ManifestError`を定義し、`load_manifest`は`ClickException`の代わりにこれを投げる（click import除去）。既存エラー文言は維持
- `commands/__init__.py`
    - `get_manifest`が`ManifestError`を従来同等の`ClickException`へ変換する（CLI出力・終了挙動不変）
- `services/backlog.py`
    - `read_backlog(manifest, project) -> str`: backlog内容を返す。resource解決は`append_backlog`と同規則
    - localはresource source配下、remoteはmount済み`_resolved_workspace_path`配下の`docs/backlog.md`を読む（SSHしない）
    - mount未済（パス不在）は`ServiceError`、ファイル不在は空文字列を返す
- `webapp/routers/`
    - `todos.py`: `GET /api/todos` → `{"pending": [...], "completed": [...]}`（services表示順）／`POST /api/todos`（title必須・project/priority/due_date任意、201で作成Todo）／`PATCH /api/todos/{id}`（`{"done": true}`のみ受理、200で更新後Todo）／`DELETE /api/todos/{id}`（204）
    - `projects.py`: `GET /api/projects` → manifest由来の名前一覧
    - `backlog.py`: `GET /api/backlog/{project}` → `{"project": ..., "content": ...}`／`POST /api/backlog/{project}`（memo必須・空白のみ不可、201）
    - `inbox.py`: `POST /api/inbox`（title・body必須、201で作成ファイル名）
    - リクエスト/レスポンスのPydanticスキーマは各ルータファイル内に定義
- `webapp/server.py`
    - APIルータをSPA catch-allより先に登録する
    - `exception_handler`で`ServiceError`→400、`NotFoundError`→404、`ManifestError`→500へ一括変換（`{"detail": メッセージ}`形式）。エンドポイント内の個別try/exceptは書かない
- manifestは必要なリクエストごとに`load_manifest()`で読む（キャッシュしない）

## 実装方針
- ルータはリソース単位で独立させ、後続ビュー追加時にファイル追加だけで拡張できる構成とする
- 入力検証はPydanticスキーマ（形式）とservices（業務規則）の2段とし、ルータへ業務判断を持ち込まない
- MMDD等のCLI固有入力形式はAPIへ持ち込まず、ISO日付（YYYY-MM-DD）のみ受ける
- `NotFoundError`は`ServiceError`の派生だが、Starletteのハンドラ解決はMRO順のため両方登録すれば区別される

## 受け入れ基準
- [ ] 全エンドポイントがTestClient経由で仕様どおりの状態変化・応答を返す
- [ ] `ServiceError`/`NotFoundError`/`ManifestError`が400/404/500へ変換される
- [ ] `GET /api/todos`の並び順がCLI表示順と一致する
- [ ] whub CLIの出力・終了挙動が変更前と一致する
- [ ] webapp・services・modelsが`click`をimportしていない
- [ ] `uv run pytest`が全件通る

## 検証条件
- 自動: TestClient+一時ディレクトリ（既存servicesテストのデータ注入パターン踏襲）でAPI・例外変換・並び順を検証。`get_manifest`の変換はCLIテストランナーで検証
- 手動: `whub app`起動後、curlでtodo追加→done→削除・backlog追記・inbox投函を実行し、ファイル実体とCLI表示を突合する

## リスク・注意点
- catch-allより後にルータを登録するとGET系APIが404になる（登録順が契約）
- remote backlogのGETはmount状態に依存。未mount時は`ServiceError`(400)が正常動作
- inboxの同一分内同タイトル連投は400（`ServiceError`）で返る（S1.5の衝突挙動踏襲）

## 確定事項
- `GET /api/todos`はpending/completedを同梱する。
- backlogファイル不在時の`GET`は空文字列で200を返す。
- `DELETE /api/todos/{id}`は204 No Contentを返す。
