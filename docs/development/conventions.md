# Development conventions

## Environment and verification

Python環境はuvで管理する。テストはrepository rootで実行する。

```sh
uv run pytest
```

変更に対応するfocused testを先に実行し、完了前に全体回帰を確認する。テスト可能な仕様はテストを実装保証として扱い、非自明な適用理由はコードまたはテストの近くに短く記録する。

## Documentation

- `README.md` は導入と主要な利用方法を扱う。
- `docs/reference/` はCLIと設定の完全な参照を扱う。
- `docs/architecture/` は現在の構造と不変条件を扱う。
- `docs/ADR/` は変更しない過去の設計判断を扱う。
- `docs/operations/` は運用runbookを扱う。
- `docs/development/` は開発者向け規約を扱う。

設計を変える判断はADRに記録する。文書は実装と同じ変更で更新し、履歴文書を現在の仕様に合わせて書き換えない。

## Project work

Project固有作業の前に `whub ls` で対象を解決し、対象rootの `AGENTS.md` を読む。remote Resourceはmount経由で参照し、横断検索や長時間処理はremote側で実行する。
