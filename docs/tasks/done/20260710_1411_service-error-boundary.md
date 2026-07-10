# 目的・前提・方針案

- 目的: services層導入で判明したエラー境界を整理し、CLI/Web adapterからClick依存を切り離す
- 経緯: `target.py`の`TargetError`が`click.ClickException`を継承しており、backlog serviceがtarget機構を再利用すると間接的にClickへ依存する
- 前提: `TargetError`はservicesから独立した純粋例外とし、servicesは必要に応じて`ServiceError`へ変換する
- 方針: I/O失敗はservicesで文脈付きの`ServiceError`へ正規化し、CLI/Web adapterが表示・プロトコル固有の例外へ変換する

# 計画

## Phase 1: 現行挙動の固定
- [x] target失敗時のcd・run・fetchのCLI出力と終了挙動をテストで固定する

## Phase 2: target境界の純化
- [x] `src/whub/target.py`からClick依存を除去し、`TargetError`を純粋例外にする
- [x] `src/whub/commands/cd.py`・`run.py`・`fetch.py`で`TargetError`を従来同等のClick例外へ変換する

## Phase 3: 検証と文書化
- [x] core・command単体テストで例外種別・出力・終了挙動を検証する
- [x] `docs/whub-concepts.md`にtargetとCLI/Web adapterのエラー責務を記録する

# 実行ログ

# 結果

- `TargetError`を純粋例外にし、cd/run/fetchのCLI表示・終了コードを維持した（`uv run pytest`: 143 passed）。
