# 目的・前提・方針案

- `whub mount` は FAIL 表示になるが、実際にはマウントできている
- 原因: sshfs(fuse-t)がrc=0で返った直後、macOSのマウントテーブル反映に0.2〜0.4秒のラグがある
- `_mount`はsshfs直後に`inspect_resource`→`is_mount()`を呼ぶため、常にFalseになる

# 計画

## Phase 1: mount後のポーリング追加
- [x] `mount.py:_mount`で、sshfs成功後に`is_mount()`をリトライするポーリングを追加（200ms間隔、最大2秒）

## Phase 2: 検証
- [x] 全リソースをunmount→`whub mount`で正常表示を確認
- [x] 既にマウント済みのリソースがskip表示されることを確認

# 実行ログ

### 試行 1: タイミング問題の検証
- 実施内容: sshfs成功後の`is_mount()`を200ms刻みで計測
- 結果: 全リソースで即時False、0.4秒後にTrue（一貫して再現）
- 判断: 続行 — ポーリングで解決可能

# 結果

- `mount.py:_mount`にポーリング（200ms×最大10回）を追加し、fuse-tのマウントテーブル反映ラグを吸収
- mount/skip両ケースで正常表示を確認
