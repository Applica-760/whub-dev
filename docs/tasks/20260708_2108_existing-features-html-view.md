# 既存機能のHTMLビュー作成

## 目的・前提・方針案
- 目的: FOCUSに依存せず、既存機能の状態をHTMLで見られるWeb appを作る
- 前提: todo、inbox、backlog、project一覧などの既存データだけでもWeb appとして成立する
- 方針: FOCUS再構成とは別タスクとして、既存機能の閲覧・軽い入力ビューから検討する

## 計画

### 確定事項（2026-07-10 相談で決定）
- 構成: ハイブリッド。FastAPI（JSON API + 静的配信）+ Vite+React SPA。Nodeは開発・ビルド時のみ
- 選定理由: whubモデル（Pydantic/paths.py）のSSOTをPython側で再利用しつつ、portfolioのReact/Mantine資産への道を残すため
- backend: `whub app`コマンドで起動。whubパッケージの既存関数（todo load/save、backlog挿入）を直接import
- frontend: リポジトリ直下`app/`に配置。distは非コミット、`whub app`がWHUB_ROOTから`app/dist`を解決
- ホスト: 当面Mac localhostのみ。スマホ対応（Tailscale等）は先送り
- 初期スコープ: todo（表示/追加/完了）+ backlog（表示/追記）
- スコープ外: FOCUSビュー・inbox書込（いずれも仕様未確定のため別タスクへ切り離し。後からのビュー追加を前提にAPIを設計）
- backlog対象: 既存target機構を流用しlocal+remote両対応（表示はmount前提、追記はCLIと同経路）
- UI: Mantine 8 + Apple風テーマ調整（部品の質・portfolio共有を優先、Apple感はテーマ層で寄せる。LiqUIdify等の新興glass系は成熟度不足で見送り）
- API案: GET/POST /api/todos、PATCH /api/todos/{id}、GET /api/projects、GET/POST /api/backlog/{project}
- 競合制御はlast-write-wins、認証・CORSなし（localhost限定）、依存追加はfastapi+uvicorn

### Phase 1: 仕様の意思決定
- [x] 現状把握（データ実体・SSOT・Node資産・backlog記載スコープの整理）
- [x] アーキテクチャ・ホスト場所・初期スコープ・配置/dist・inbox扱いを決定（上記確定事項）

### 仕様書の発行方針（2026-07-10 追加決定）
- 機能が大きいため1文書にせず、作業単位ごとに複数の実行仕様書へ分割発行する
- 各仕様書は関数単位まで詳細化し、内容ごとにユーザと合意してから確定する
- 本mdは全仕様書を束ねるロードマップとして使う（粒度の妥当性・完成までの残作業をここで管理）

### Phase 2: 仕様書の分割発行（ロードマップ）
- [x] S1: server基盤設計 — `docs/specs/20260710_0947_whub-app-s1-server-foundation.md`（ポート8710・自動オープン・127.0.0.1固定で確定）
- [x] S1.5: inbox投函のservices層 — `docs/specs/20260710_1630_whub-app-s1.5-inbox-service.md`（title必須・日時プレフィックス自動付与・空body不許容・manifest経由でvault解決）。APIはS2bへ、UIフォームはS4へ組み込む
    - 役割整理済み（2026-07-10）: inboxは対話抜きで思いつきを書き殴る摩擦ゼロの投函口。project非紐付けでbacklogとは別軸。CLIコマンドは作らない。会話・整理は投函後のSkill（refile等）が担う
    - [x] 実装: `services/inbox.py`と単体テストを追加（`uv run pytest`: 164 passed）
- [x] S2a: サービス層抽出 — `services/`新設（todo・backlog・errors）、commands痩身化。CLI振る舞い不変の純粋リファクタ。concepts docの責務境界更新を含む
- [x] S2b: リソースAPI設計 — `docs/specs/20260710_1853_whub-app-s2b-resource-api.md`（todo一覧はpending/completed同梱、backlog未作成は空文字列200、todo削除は204で確定）
- [x] S3: フロント基盤設計 — `docs/specs/20260710_2153_whub-app-s3-frontend-foundation.md`（npm・openapi-typescript・生成型コミット・React Router導入で確定）
- [ ] S4: ビュー設計 — Todoビュー・Backlogビューのコンポーネント構成
- [ ] S5（検討中）: Agent連携ブリッジ — Web UIからdiscourse Skill呼び出し（URL渡し→回答取得）。headless Claude起動・非同期実行・タイムアウト・権限の設計が必要で、単純なファイルAPIとは別次元の部品
- 発行順の理由: S2のAPI契約が前後端の境界のため、S1→S2で契約を固めてからS3/S4へ進む。S1.5/S5は仕様議論が先行

### S2の層分離方針（2026-07-10 決定）
- CLIとwebappは、`services/`の業務処理を呼ぶ別々のアダプタとして分離する
- 配置規則: modelsはデータ・検証・load/save、servicesは操作（採番・状態遷移・target振り分け等のI/Oを伴う手順）
- servicesはClick/HTTP非依存のドメイン例外を投げ、CLIはClickException、webはHTTPExceptionへ変換する
- webappから内部操作のためにCLI・シェルを実行しない。外部プロセス実行はS5で別途設計する
- 既存平置きモジュールのcore/移設は別タスクへ分離 → `docs/tasks/20260710_1319_core-package-restructure.md`
- concepts docの「ドメイン処理は各コマンド側に置く」記述はS2aで責務境界を更新する

### S2bのAPI設計方針（2026-07-10 決定）
- エンドポイント: GET/POST `/api/todos`、PATCH `/api/todos/{id}`（done化のみ）、DELETE `/api/todos/{id}`、GET `/api/projects`、GET/POST `/api/backlog/{project}`、POST `/api/inbox`（S1.5のservice公開）
- GET `/api/projects`はTab補完と同じmanifest由来の名前一覧のみ返す（名前一意・resource無しはworkspace-hubのみのため属性不要）
- backlog読取はservicesに読取関数を新設し、mount前提で`_resolved_workspace_path`から読む（SSHしない）
- manifest境界: `load_manifest`を純粋例外`ManifestError`化し、CLIは`get_manifest`の1箇所で変換（TargetError純化`done/20260710_1411`の前例踏襲）
- エラー変換はFastAPIの`exception_handler`で一括（`ServiceError`→400、`NotFoundError`→404、`ManifestError`→500）。各エンドポイントにtry/exceptは書かない
- 構成は`webapp/routers/`にリソース別ルータ（todos/projects/backlog/inbox）。スキーマは各ルータ内に置き、共有が生じるまで`schemas.py`は作らない
- APIルータはSPA catch-allより先に登録する（Starletteは登録順マッチのため）

### S3のフロント基盤方針（2026-07-10 決定）
- 配置はリポジトリ直下`app/`（確定事項どおり）。`src/whub`へは含めない（Pythonパッケージ境界・npm/uvツールチェーン分離のため）
- 型生成はopenapi-typescript。FastAPIの`openapi.json`をサーバ起動なしでexportし、TS型を生成。クライアントは薄い手書きfetchラッパ（orvalはsns-labと共通化できるが周辺選定を引き連れるため見送り）
- ルーティングはReact Routerを雛形から導入（S1のSPAフォールバックが前提済み）。初期ルートは`/todos`・`/backlog`
- 再利用方針: sns-lab基盤（pnpm workspace+Turbo）の移植はしない。ただし統合を見越し`theme/`・`components/`（ドメイン非依存）と`features/`・`api/`（whub固有）を分離し、2つ目の利用者が現れた時点でパッケージ抽出する
- テーマはiOS設定画面風grouped listイメージ（背景#f2f2f7・白カード・角丸10〜12px・影なし・`-apple-system`フォント）をMantineテーマ層で定義。grouped list部品はS4で作る
- 開発時はVite devサーバの`/api`プロキシで`127.0.0.1:8710`へ転送
- パッケージマネージャはnpm（S1のdist欠如案内文言と一致・追加ツール不要）
- 生成型はコミット対象（プライベートリポのためclone即ビルド可を優先。API変更時は再生成とセットでコミット）

### S3 実装計画（2026-07-10 確定）
- [x] Phase 1: `whub.webapp.openapi`でサーバー不要のOpenAPI出力を追加し、生成対象をPythonテストで固定する
- [x] Phase 2: `app/`へVite・React・Mantine・ルーティング・テーマ・API型生成基盤を追加する
- [x] Phase 3: 開発フローを文書化し、依存導入後にbuild・型生成・APIプロキシ・既存テストを検証する

### Phase 3: 実装（仕様書ごとに実施・検証）
- [ ] 各仕様書単位で実装し、受け入れ基準で検証する

### S2b 実装計画（2026-07-10 確定）
- [x] Phase 1: manifest例外境界とbacklog読取serviceを追加し、既存CLI挙動をテストで固定する
- [x] Phase 2: todo・projects・backlog・inboxのAPIルータと共通例外変換を追加する
- [x] Phase 3: TestClient・CLI・全件テストでAPI契約を検証する（S3前のため手動curlは未実施）

### 完成までの残作業（仕様書化前の候補）
- Apple風テーマの具体化（S3で方針、深掘りは必要なら別仕様書）
- inbox投函フォームの仕様（タイトル要否・ファイル名規則）→ S1.5の仕様書化で確定
- refile Skillの拡張構想: 配置相談だけでなく内容の議論・セッションも担う（別途Skill改修として検討）
- discourse連携の実行モデル設計（同期/非同期・結果の受け渡し場所）→ S5の前提
- 後続の別タスク: FOCUSビュー・スマホ対応（Tailscale）

## 実行ログ

### 試行 1: S1 server基盤のTestClient検証
- 実施内容: FastAPI・uvicorn追加後に新規テストを実行
- 結果: Starlette TestClientが開発依存`httpx2`を要求
- 判断: `httpx2`をdev依存へ追加して継続

### 試行 2: S2b APIテスト
- 実施内容: 新規`/api/todos`に合わせ、SPAフォールバック禁止テストの未定義APIを変更
- 結果: 対象31件・全体177件が通過
- 判断: 続行

### 試行 3: S3 TypeScript型検査
- 実施内容: 生成型を含めて`npm run typecheck`を実行
- 結果: CSS importのVite型宣言が未登録で失敗
- 判断: `vite/client`型参照を追加して継続

### 試行 4: S3 Viteビルド
- 実施内容: `npm run build`を実行
- 結果: Codex非対話シェルのNode v20 x64とユーザー環境のNode v24 arm64が不一致で失敗
- 判断: Node v24をPATH先頭に固定して再実行し、Vite build成功

### 試行 5: S3手動確認
- 実施内容: ローカルブラウザ接続後に配信・直接URL・Vite proxyを確認
- 結果: ブラウザ接続は実行環境エラーのため、HTTP応答で`/todos`・`/api/health`・proxyを確認
- 判断: 静的配信とAPI proxyは検証済みとして継続

## 結果
