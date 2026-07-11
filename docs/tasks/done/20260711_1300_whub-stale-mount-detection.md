# 目的・前提・方針案

## 目的
- stale sshfsマウント（プロセス死・マウントエントリ残存）を`whub status`/`whub mount`が正しく検知できるようにする

## 前提（2026-07-11の障害診断結果）
- 事象: IL（la-imitation-learning）のsshfsプロセスが消失、マウントエントリのみ残存。実I/O（readdir）は無限ハングするのに`whub status`は「ok」と誤報告
- 原因: fuse-tはFUSEをlocalhost NFSとして見せるため、`inspect_mount`（health.py）の`stat`チェックはNFS属性キャッシュから即答（0.007s）してしまい、死活を検知できない
- 波及: `whub mount`も同じ`inspect_mount`で「ok→skip」判断するため、staleなマウントを素通しして張り直せない
- プロセス死の直接原因は特定不能（クラッシュログなし）。スリープ/ネットワーク遷移時のsshfs死は環境要因で、設定差はなくどのリソースでも再発し得る
- 検知手法の実証済み: `pgrep -f 'volname=whub-<name>'`が生存マウントでexit 0、死んだマウントでexit 1を正確に返す

## 方針案
1. 【必須】`inspect_mount`にsshfsプロセス生存チェックを追加（mount tableにあるのにプロセスなし→stale）。volname導出のためproject名を渡すシグネチャ変更が必要
2. 【補助・任意】`stat`をsubprocess+timeoutの`listdir`に置換（readdirはハングするためtimeoutで検知可能）
3. 【要判断】stale検知時の自動修復（force unmount→remount）は`whub mount --repair`等の明示オプションとする（force unmountは書き込み中データ喪失リスクがあるため自動化しない）
4. 【スコープ外】watchdogによる予防（launchd agent / whub appサーバでの定期チェック＆remount）は本タスクでは扱わない

# 計画

## Phase 1: 検知修正
- [x] `health.py`の`inspect_mount`でstatより先にvolnameベースのsshfsプロセス生存を確認する
- [x] `status`・`mount`・`unmount`からproject名を渡し、プロセス消失を`stale`として扱う
- [x] プロセス生存・消失・検査失敗とCLIのstale導線をunit testで回帰確認する

## Phase 2: 修復導線
- [x] 既存の`whub unmount --force <project>`→`whub mount <project>`を修復導線として検証する（`--repair`は追加しない）

# 実行ログ

# 結果

- `inspect_mount`がsshfsプロセス消失を`stale`として検知し、`stat`の属性キャッシュによる誤判定を防止
- `status`はstaleで終了コード1、`mount`はsshfsを起動せず、`unmount --force`で明示的に修復可能
- `uv run pytest -q`: 188 passed
