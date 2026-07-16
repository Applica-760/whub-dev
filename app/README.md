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

別ターミナルでリポジトリルートから`whub app --no-open`を起動してから、Viteを起動する。

```sh
npm run dev
```

Viteは`/api`を`http://127.0.0.1:8710`へプロキシする。

## ビルドと検証

```sh
npm run typecheck
npm run build
uv run pytest
```

`npm run build`の出力先は`app/dist/`であり、`whub app`が静的配信する。
