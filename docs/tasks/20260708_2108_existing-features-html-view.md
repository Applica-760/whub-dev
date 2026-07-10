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
- [ ] S1.5（検討中）: inbox — Web appと同等に重要。**whubコマンドではなくSkillとしての実装を見越す**ため、Web appからの書込経路（直接ファイル書込か、Skill経由か）の整理が先
- [ ] S2: リソースAPI設計 — todo/projects/backlogのエンドポイント・スキーマ・既存関数への対応付け。肥大化するならtodo系とbacklog/projects系に分割
- [ ] S3: フロント基盤設計 — `app/`雛形・ルーティング・APIクライアント・テーマ方針
- [ ] S4: ビュー設計 — Todoビュー・Backlogビューのコンポーネント構成
- [ ] S5（検討中）: Agent連携ブリッジ — Web UIからdiscourse Skill呼び出し（URL渡し→回答取得）。headless Claude起動・非同期実行・タイムアウト・権限の設計が必要で、単純なファイルAPIとは別次元の部品
- 発行順の理由: S2のAPI契約が前後端の境界のため、S1→S2で契約を固めてからS3/S4へ進む。S1.5/S5は仕様議論が先行

### Phase 3: 実装（仕様書ごとに実施・検証）
- [ ] 各仕様書単位で実装し、受け入れ基準で検証する

### 完成までの残作業（仕様書化前の候補）
- Apple風テーマの具体化（S3で方針、深掘りは必要なら別仕様書）
- inbox運用形式の確定（1トピック1md等）とSkill化の設計 → S1.5の前提
- discourse連携の実行モデル設計（同期/非同期・結果の受け渡し場所）→ S5の前提
- 後続の別タスク: FOCUSビュー・スマホ対応（Tailscale）

## 実行ログ

## 結果
