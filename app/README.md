# whub app 開発

## 初回セットアップ

```sh
npm install
```

## 型生成

```sh
npm run generate:types
```

`generate:types`はサーバーを起動せず、`uv run --project .. python -m whub.webapp.openapi`からOpenAPIスキーマを出力して`src/api/generated/schema.d.ts`を更新する。API変更時は生成物もコミットする。

## 開発

Whub contextからdevelopment checkoutのCLIを選び、開発モードを起動する。

```sh
uv run --project ./whub whub app dev
```

画面は`http://127.0.0.1:8712`で配信され、ViteのHMRとFastAPIのリロードが有効になる。`/api`は内部のFastAPI（`8713`）へプロキシされる。停止は`uv run --project ./whub whub app down --dev`を使う。配布版の`whub app`は`8710`を使用するため、同時に起動できる。

## ビルドと検証

```sh
npm run typecheck
npm run build
uv run pytest
```

`npm run build`の出力先は`src/whub/webapp/dist/`であり、Whub wheelへpackage resourceとして同梱される。`app/`はfrontend sourceだけを管理する。
