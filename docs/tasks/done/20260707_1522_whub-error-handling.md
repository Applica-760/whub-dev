# 目的・前提・方針案

- 目的: whubの設定・manifest読み込み失敗を、利用者が次に取るべき行動が分かるエラーへ整形する
- 前提: root/data_dir解決は`paths.py`に集約済みで、通常は`.whub/config.toml`の`data_dir`を読む
- 対象: manifest欠落・YAML不正・Pydantic検証エラー
- 方針: 既知のmanifest読取失敗だけClickExceptionへ変換し、未知例外は握りつぶさない

# 計画

## Phase 1: manifest読取エラーの境界を絞る
- [x] `load_manifest()`でmanifest欠落・YAML不正・schema不正のみ扱う方針に決定
- [x] それ以外の未知例外は握りつぶさず現状通り漏らす

## Phase 2: 実装
- [x] `load_manifest()`でmanifest欠落・YAML不正・schema不正のみ`click.ClickException`へ変換する
- [x] `test_manifest.py`に欠落・YAML不正・schema不正のClickException化を追加する

## Phase 3: 検証
- [x] 関連unittestを実行する

# 実行ログ

### 試行 1: 全unittestを通常入口で実行できる
- 実施内容: `uv run python -m unittest`
- 結果: 0件検出で終了
- 判断: 方針変更

### 試行 2: unittest discoverで全テストを検出する
- 実施内容: `uv run python -m unittest discover -s src/whub/tests`
- 結果: 62件OK
- 判断: 続行

# 結果

- `load_manifest()`でmanifest欠落・YAML不正・schema不正を`ClickException`へ変換した
- 関連unittest 21件、全discover 62件、代表CLI表示を確認済み
