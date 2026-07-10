# manifest由来のVS Code除外設定生成コマンド

## 目的・前提・方針案
- 目的: whubが作るmount/symlinkツリーを、manifestから導出した`.vscode/settings.json`除外設定でVS Codeの走査対象から外す
- 前提: `projects/LAplust/IL`のfuse-t mountがVS Codeのウォッチャ/Pylance走査をブロックし、symlink先約20万ファイルがインデックスを肥大化させている（2026-07-10調査）
- 前提: 全resourceは`workspace_path`必須のため、除外リストはmanifest.yamlから機械的に導出できる（二重管理の回避）
- 方針: VS Code固有の独立サブコマンド`whub vscode`で冪等生成する（mount/link自動更新やbootへの組み込みは見送り、2026-07-10決定）
- 方針: manifestのsymlinkとmount対象をwatcher/search/Python解析から一律に除外する
- 方針: settings.jsonはwhub管理キーのみ上書きし、手書き設定を保持する

## 計画
### Phase 1: CLIコマンド
- [x] `commands/vscode.py`にManifest→除外設定の導出・既存settings.jsonとのマージ・`whub vscode`を実装（CLI専用のためservices層は設けない）
- [x] `tests/commands/test_vscode.py`にresource種別ごとの生成・手書き設定保持・冪等性テストを追加
- [x] `docs/whub-concepts.md`のコマンド一覧へ`vscode`を追記

### Phase 2: 検証
- [x] `uv run pytest`全通過を確認
- [x] テストmanifestで`whub vscode`のsettings.json生成と冪等性を確認

## 実行ログ

## 結果
- `whub vscode`がsymlinkとmount対象をwatcher/search/Python解析から除外し、手書き設定を保持して冪等更新する
- `uv run pytest`は166件、`uv run whub --help`は`vscode`登録を確認
