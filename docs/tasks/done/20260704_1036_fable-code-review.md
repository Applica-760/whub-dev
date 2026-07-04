# 目的・前提・方針案

## 目的
Fable 5によるコードレビュー（2026-07-04）の指摘を網羅記録し、後日対応する。

## 前提
- レビュー範囲: `HEAD~3..HEAD`（1068bd7 remote mount base / ee10837 mount再実装 / 99e3382 fetch追加）
- レビュー時点でテスト40件は全て通過。クラッシュ級のバグはなし
- `docs/roadmap.md`の既知課題（CWD依存・ControlMaster等）は除外済み
- 判定: CONFIRMED=コードから確認済み / PLAUSIBLE=現実的な条件で発生しうる

## 方針案
- 正確性の退行（Phase 1）を最優先、mount/health系はリファクタ1回でまとめて解消（Phase 2）
- 各修正は既存テストを壊さず独立に導入可能

# 計画

## Phase 1: status 正確性【CONFIRMED / PLAUSIBLE】
- [x] git取得失敗が「0 files」表示になる退行を修正（`status.py`。プローブに`git rev-parse`の成否マーカーを追加し、失敗時は`?`を返す）【CONFIRMED】
- [x] プローブtimeout=15秒固定をリソース数でスケールさせる（`status.py`。旧実装のリソース毎8秒に合わせ`5 + N*8`）【PLAUSIBLE】

## Phase 2: mount / health の堅牢性・効率
- [x] マウント成功待ちループを`in_mount_table`のみに変更（`mount.py`。statはループ後に1回）【CONFIRMED】
- [x] mountテーブル取得のTimeoutExpiredを捕捉（`health.py`の`read_mount_table`。失敗時は空テーブル→unmounted扱い）【PLAUSIBLE】
- [x] mountテーブルをコマンド冒頭1回取得に変更（`inspect_mount`に`mount_table`引数を追加し、status/mount/unmountが共有）【CONFIRMED】
- [x] sshfs失敗時に作成済みの空mountpointディレクトリを掃除（`mount.py`の`_cleanup_mountpoint`。rmdirなので空でなければ触らない）【PLAUSIBLE・軽微】
- [x] dead codeの`inspect_remote`を削除（`inspect_resource`ごと削除し、link.pyは`inspect_symlink`直呼びへ。whub-conceptsのhealth.py記述も更新）【CONFIRMED】
- [ ] 調査: 接続断時にmacOSが出す「無視/アンマウント」ダイアログの抑止（fuse-tのNFS層由来かの切り分け → sshfsのreconnect/ServerAlive調整、切断検知時の自動unmount等を比較検討）

## Phase 3: fetch / scp
- [x] `build_scp_command`にBatchMode/ConnectTimeout=5を追加（`remote.py`。他ビルダーと整合）【PLAUSIBLE】
- [x] scpリモートパスのglob解釈対策（`remote.py`の`_escape_scp_glob`で`\*?[]`をエスケープしリテラルパス化）【PLAUSIBLE】

## Phase 4: manifest 検証
- [x] workspace_pathの重複をmanifest検証に追加（`models/manifest.py`。project名重複検証と同型）【PLAUSIBLE】

## Phase 5: 検証
- [x] テスト46件（+6件追加）全通過（`uv run python -m unittest discover -s src/whub/tests`）
- [x] プローブスニペットを実シェルで検証（非リポジトリ→`?`、リポジトリ→件数。BSD wcのパディングは`split()`が吸収）
- [x] 実機`whub status`確認（remote 3件 mount ok・git件数表示・exit 0）
- [ ] mount不達ホストのFAIL挙動・空mountpoint掃除の実機確認

# 実行ログ

### 試行 1: プローブのgit成否マーカー方式
- 実施内容: `wc -l`単独では失敗と0件が同値になるため、`git rev-parse --is-inside-work-tree && ... | wc -l || echo '?'`の2段構成に変更
- 結果: 実シェル検証で非リポジトリ→`?`、リポジトリ→件数を確認。`echo '?'`はglob展開防止のためクォート必須
- 判断: 続行

# 結果
- レビュー指摘10件のうち9件を修正完了。テスト40→46件全通過、実機statusも正常
- 残: macOSダイアログ抑止の調査（追加項目）、mount失敗系の実機確認
