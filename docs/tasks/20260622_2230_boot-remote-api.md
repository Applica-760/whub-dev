# 目的・前提・方針案

`whub boot`のremote操作を`remote.py`の接続・実行APIへ集約し、内部利用目的だった`whub run`を廃止する。

# 計画

## Phase 1: remote実行基盤
- [ ] `remote.py`にSSH実行とrsync実行の結果を統一的に返すAPIを追加する

## Phase 2: boot移行
- [ ] `boot.py`のremote読込・書込・skills同期・CodeGraph初期化を共通API利用へ変更する
- [ ] remote処理の失敗を戻り値で検出できるテストを追加する

## Phase 3: run廃止
- [ ] `run.py`・CLI登録・run固有テストを削除し、READMEとADRを更新する

## Phase 4: 検証
- [ ] 関連テスト・CLI help・差分検査を実行する

# 実行ログ

# 結果
