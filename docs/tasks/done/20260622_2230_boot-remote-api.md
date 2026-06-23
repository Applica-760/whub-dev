# 目的・前提・方針案

`whub boot`のremote操作を`remote.py`の接続・実行APIへ集約し、内部利用目的だった`whub run`を廃止する。

# 計画

## Phase 1: remote実行基盤
- [x] `remote.py`にSSH実行とrsync実行の共通APIを追加する

## Phase 2: boot移行
- [x] `boot.py`のremote読込・書込・skills同期・CodeGraph初期化を共通API利用へ変更する
- [x] remote処理の失敗を検出し、後続対象を処理するテストを追加する

## Phase 3: run廃止
- [x] `run.py`・CLI登録・run固有テストを削除する
- [x] READMEとADRを現行CLIへ更新する

## Phase 4: 検証
- [x] 関連テスト・CLI help・差分検査を実行する

# 実行ログ

- `python -m unittest discover -s src/whub/tests -v`: 12件成功
- `whub --help`: `boot`、`cd`、`link`、`shell-init`、`status`のみ提供されることを確認
- 文書横断検索で公開CLIの`whub run`とSSHFS前提を現行文書から除去

# 結果

remote操作を`remote.py`のSSH・rsync実行基盤へ集約した。`whub boot`は対象単位の失敗を警告して後続処理を継続する。内部利用目的だった`whub run`は実装・CLI・テストから削除した。
