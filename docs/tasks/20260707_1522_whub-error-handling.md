# 目的・前提・方針案

- 目的: whubの設定・manifest読み込み失敗を、利用者が次に取るべき行動が分かるエラーへ整形する
- 前提: root/data_dir解決は`paths.py`に集約済みで、通常は`.whub/config.toml`の`data_dir`を読む
- 対象: config欠落・data_dir不正・manifest欠落・YAML不正・Pydantic検証エラー・`version: 2`のcoerce
- 方針: tracebackを避け、ClickExceptionとして短く具体的に出す

# 計画

## Phase 1: エラー境界の整理
- [ ] manifest/config読み込みでユーザーに見せるエラー種別を決める
- [ ] `version`の許容・coerce方針を決める

## Phase 2: 実装
- [ ] `paths.py`/`load_manifest()`/`get_manifest()`周辺で例外を整形する
- [ ] manifest検証エラーの表示をCLI向けに短くする

## Phase 3: 検証
- [ ] 欠落・不正config・不正manifest・`version: 2`のテストを追加する
- [ ] 全テストと代表CLIでエラー表示を確認する

# 実行ログ

# 結果
