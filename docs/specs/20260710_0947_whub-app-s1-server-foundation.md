# 実行仕様書: whub app S1 — server基盤

## 目的
- `whub app`コマンドでlocalhostにFastAPIサーバを起動し、SPA静的配信と後続APIの登録口を持つ基盤を作る

## 背景・前提
- whub app全体の意思決定とロードマップは`docs/tasks/20260708_2108_existing-features-html-view.md`を正とする
- 分割発行の1本目。後続はS2（リソースAPI）・S3（フロント基盤）・S4（ビュー）
- フロントエンド`app/`はS3で作成するため、本仕様ではdist欠如時の挙動も定義する
- ホストはMac localhost限定。認証・CORSは持たない

## 対象範囲
- `src/whub/webapp/server.py`（新規）
- `src/whub/commands/app.py`（新規）
- `src/whub/paths.py`（関数追加）
- `src/whub/cli.py`（コマンド登録）
- `pyproject.toml`（依存追加）
- `.gitignore`（`app/dist/`追加）
- `src/whub/tests/test_webapp_server.py`（新規）

## 非対象範囲
- todo/projects/backlogのリソースAPI（S2）
- フロントエンド一式（S3/S4）
- 認証・CORS・LAN/リモート公開・スマホ対応

## 変更要件
- `paths.py`
    - `app_dist_path() -> Path`: `whub_root() / "app" / "dist"`を返す
- `webapp/server.py`
    - `create_app(dist_dir: Path) -> FastAPI`: アプリファクトリ
        - `GET /api/health`が`{"status": "ok"}`を返す
        - `dist_dir`配下を静的配信する
        - `/api`以外の未マッチGETパスへ`index.html`を返す（SPAフォールバック）
        - S2以降のリソースルータを登録できる受け口を持つ
- `commands/app.py`
    - `app`（Click command）: オプションは`--port`（int・デフォルト8710）と`--no-open`（flag）
    - `app_dist_path()`に`index.html`が無ければ、ビルド手順（`cd app && npm install && npm run build`）を含む`ClickException`で終了する
    - bind先は`127.0.0.1`固定でuvicornを起動する
    - 起動時にデフォルトでブラウザを開き、`--no-open`で抑止できる
- `cli.py`: `main.add_command(app)`を追加
- `pyproject.toml`: `fastapi`・`uvicorn`をdependenciesへ追加

## 実装方針
- `webapp/`は`remote.py`等と同列のドメイン低レイヤーとし、`commands/app.py`は引数整形・案内・起動のみ担う（`docs/whub-concepts.md`のCLI設計ポリシー踏襲）
- `create_app`が`dist_dir`を引数で受けるのは、テストで一時ディレクトリを注入するため
- ブラウザオープンは標準ライブラリの薄い呼び出しとし、失敗してもサーバ起動を妨げない
- SPAフォールバックはS3以降のクライアントルーティングを想定した仕様である

## 受け入れ基準
- [ ] dist存在時に`whub app`でサーバが起動し、`http://127.0.0.1:8710/api/health`が`{"status": "ok"}`を返す
- [ ] 非APIパスへのGETが`index.html`の内容を返す
- [ ] dist欠如時にビルド手順の案内を表示して終了する（スタックトレースを出さない）
- [ ] デフォルトでブラウザが開き、`--no-open`で抑止できる
- [ ] `--port`でポートを変更できる
- [ ] `uv run pytest`が全件通る（新規テストを含む）

## 検証条件
- 自動: TestClientでhealth・静的配信・SPAフォールバックを検証。dist欠如時の案内はClickのテストランナーで検証。一時ディレクトリをdist_dirとして注入する
- 手動: ダミーの`app/dist/index.html`を置いて`whub app`を起動し、ブラウザ表示とhealth応答を確認する

## リスク・注意点
- ポート使用中の起動失敗はuvicornのエラー表示に委ねる（追加ハンドリングはしない）
- `app/dist`はgitignore対象のため、S3完了まではdist欠如案内が出るのが正常動作である

## 不明点・確認事項
- なし（ポート8710・ブラウザ自動オープン・127.0.0.1固定・分割粒度は相談済み決定事項）
