# 実行仕様書: whub app S3 — フロント基盤

## 目的
- `app/`にVite+React+TS+Mantineの雛形を作り、ルーティング・型生成・テーマ・開発プロキシを備えたS4（ビュー実装）の土台を確立する

## 背景・前提
- 設計方針は`docs/tasks/20260708_2108_existing-features-html-view.md`の「S3のフロント基盤方針（2026-07-10 決定）」を正とする
- S2bまで実装済み。APIは`/api/todos`・`/api/projects`・`/api/backlog/{project}`・`/api/inbox`（契約は`docs/specs/20260710_1853_whub-app-s2b-resource-api.md`）
- `whub app`は`app/dist`を静的配信し、SPAフォールバック実装済み。dist欠如時の案内は`cd app && npm install && npm run build`（S1仕様）
- `.gitignore`に`app/dist/`登録済み。Node v24利用可
- パッケージマネージャはnpm。生成型はコミット対象とする（2026-07-10 確定）

## 対象範囲
- `app/`一式（新規: Vite+React+TSプロジェクト）
- OpenAPIスキーマの出力手段（whub側・サーバ起動不要）と型生成の組み込み
- `docs/`への開発フロー記録（起動・型生成・ビルドの手順）

## 非対象範囲
- Todoビュー・Backlogビュー・inboxフォームの実装（S4）
- grouped list等の再利用コンポーネント実装（S4で必要になった時点で`components/`へ）
- UIテスト基盤（vitest等）の導入（S4で判断）
- パッケージ抽出・モノレポ化（2つ目の利用者が現れた時点で検討）

## 変更要件
- `app/`雛形
    - Vite+React+TS。依存は`@mantine/core`・`@mantine/hooks`・`react-router`、devに`openapi-typescript`（Mantine動作に必要なpostcss設定を含む）
    - `npm run build`で`app/dist/`にビルドされ、`whub app`がそのまま配信できる
    - devサーバは`/api`を`http://127.0.0.1:8710`へプロキシする
- ディレクトリ規約（統合を見越した分離）
    - `src/theme/`: Apple風Mantineテーマ（ドメイン非依存・将来抽出候補）
    - `src/components/`: 汎用部品置き場（S3では空でよい）
    - `src/features/`: whub固有ビュー（S3ではプレースホルダ）
    - `src/api/`: 生成型+fetchラッパ（whub固有）
- ルーティング
    - React Routerで`/todos`・`/backlog`の2ルート+`/`→`/todos`リダイレクト。各ルートはプレースホルダページ
    - 2ルートを行き来できるナビゲーションを持つ最小レイアウト（シェル）を作る
- 型生成
    - whub側にサーバ起動なしで`openapi.json`を出力する手段を用意する
    - `app/`のnpm scriptでスキーマ出力→`openapi-typescript`による型生成まで一括実行できる
    - 生成物は`src/api/generated/`等の生成専用置き場に隔離し（手編集しない）、コミット対象とする
- APIクライアント
    - 生成型を使う薄いfetchラッパを`src/api/`に置く。エラーは`{"detail": string}`形式（S2bのexception_handler仕様）を解釈して例外化する
- テーマ
    - `src/theme/`にiOS設定画面風のテーマトークンを定義: 背景`#f2f2f7`・白サーフェス・角丸10〜12px・影なし・`-apple-system`系フォントスタック
    - プレースホルダページに白カード1枚を置き、テーマの見た目を確認できるようにする

## 実装方針
- Viteの公式React+TSテンプレートを起点にし、独自のビルド設定を増やさない
- テーマはMantineのテーマオブジェクト+最小のグローバルCSSに閉じ、コンポーネント個別のスタイル上書きを避ける（Apple感はテーマ層で寄せる方針）
- 生成型をコミットする運用のため、API変更時は再生成とセットでコミットする
- lint/formatはテンプレート既定の範囲に留め、sns-lab流のeslint共通化は統合検討時に行う

## 受け入れ基準
- [ ] `cd app && npm install && npm run build`が成功し、`whub app`でブラウザ表示できる
- [ ] `/todos`・`/backlog`へ直接URLアクセスしても表示される（SPAフォールバック経由）
- [ ] devサーバ経由で`/api/health`が200を返す（プロキシ動作）
- [ ] 型生成scriptが`openapi.json`出力から型生成まで一括で成功し、生成型にS2bの全エンドポイントが含まれる
- [ ] fetchラッパがAPIエラーの`detail`を例外として扱える
- [ ] `tsc`（typecheck）が通る
- [ ] 背景グレー+白カードのテーマが両ルートに適用されている

## 検証条件
- 自動: `npm run build`・typecheck・型生成scriptの成功。既存`uv run pytest`が全件通ること（whub側にスキーマ出力手段を足すため）
- 手動: `whub app`起動でブラウザ表示・2ルートの行き来・直接URLアクセスを確認。devサーバでプロキシ経由のAPI応答を確認

## リスク・注意点
- Mantineはpostcss設定（`postcss-preset-mantine`）が無いとスタイルが崩れる。雛形段階で組み込むこと
- 生成型をコミットするため、API変更時の再生成漏れは型不一致として現れる（API変更とセットで再生成する運用）
- `whub app`のdist欠如案内（`npm install && npm run build`）と実際のビルド手順が一致していることを確認する

## 不明点・確認事項
- なし（パッケージマネージャ=npm・生成型コミットは相談済み決定事項）
