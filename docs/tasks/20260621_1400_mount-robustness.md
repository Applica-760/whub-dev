# mount/unmount のロバスト性改善

## 目的・前提・方針案

### 目的
`whub mount/unmount` がネットワーク断・スリープ復帰等の異常系で壊れた状態に陥らないようにする

### 前提
- 対象: `src/whub/commands/mount.py`
- sshfsオプション `reconnect`, `ServerAliveInterval=15`, `ServerAliveCountMax=3` は設定済み
- デーモン・watchdog等の常駐プロセスは存在しない

### 現状分析

| # | 課題 | 影響 | 原因箇所 |
|---|------|------|----------|
| 1 | staleマウントを検出できない | `is_mount()`がTrueを返すため`_mount_one`がskipし、壊れたマウントが放置される | `_mount_one` L36 |
| 2 | `subprocess.run`にtimeoutがない | sshfs接続試行中にネットワーク不通だとCLIが無限ブロック | `_mount_one` L55 |
| 3 | staleマウントのunmountが失敗しうる | 素の`umount`ではstale FUSEマウントを解除できない場合がある | `_unmount_one` L66 |
| 4 | オフライン復帰後の自動再マウントなし | sshfsプロセスが死んでいた場合、手動で`whub mount`を再実行する必要がある | 機能未実装 |

### 方針案
- 課題1〜3はCLIコマンド内で対処可能（stale検出・timeout・force unmount）
- 課題4はスコープ次第（launchdデーモン等が必要で複雑度が上がる）

## 計画

（方針確定後に記録）

## 実行ログ

（実装時に記録）

## 結果

（完了時に記録）
