# whub 残作業（統合）

## 概要

全残タスクを依存関係に基づいて Phase 順に再構成したもの。
各Phaseは前Phaseの完了を前提とする（Phase 5のみ独立して着手可能）。

---

## Phase 1: shell・外部コマンド境界の整理（基盤安定化）

元タスク: refactoring Phase 4

### 方針決定
- 対応OSはmacOS。OS分岐コード・導入案内の分岐は不要（現状維持）
- `-s` フラグは意図的に維持（ADR-0007）
- `--shell` オプションは削除。zsh専用と明確化
- remote SSH は `os.execvp` で直接実行（eval 廃止）
- shell関数テンプレートは `cd.py` に移動（cd の挙動と密結合のため）

### 実行手順

#### Step 1: SSH接続情報の共通化
- [ ] `commands/__init__.py` に `build_ssh_command(host: Host, remote_path: str) -> list[str]` を定義
  - バリデーション + identity展開 + shlex.quote を集約し、`list[str]` を返す
- [ ] `commands/cd.py`, `commands/mount.py`, `health.py` をヘルパー利用に書き換え

#### Step 2: cd remote を os.execvp 化 + shell関数を cd.py に移動
- [ ] `cd.py`: remote の場合 `isatty()` で分岐 — TTY なら `os.execvp("ssh", cmd)`、非TTY なら exit 100（合図のみ）
- [ ] shell関数テンプレートを `cd.py` に移動。exit 100 時はキャプチャなしで `command whub cd "$2"` を再実行
- [ ] `shell_init.py`: `cd.py` からテンプレートを import して出力するだけに簡素化

#### Step 3: `--shell` オプション削除
- [ ] `shell_init.py` から `--shell` パラメータと `if shell_type == "zsh":` 分岐を除去、zsh補完を無条件出力

#### Step 4: sshfsパス一括解決
- [ ] `_mount_all` で `_require_sshfs()` を1回呼び、`_mount_one` に `sshfs_path` 引数で渡す

### 受け入れ基準
- SSH接続コマンド構築が `build_ssh_command` に集約（cd/mount/healthで重複なし）
- shell関数に `eval` が含まれない
- remote SSH が `os.execvp` で直接実行される
- `whub shell-init` に `--shell` オプションなし
- `_require_sshfs()` 呼出が `_mount_all` の1箇所のみ
- `eval "$(whub shell-init)"` 後、`whub cd` が動作する

---

## Phase 2: mount ロバスト性改善

元タスク: mount-robustness

### 方針決定
- `-s` フラグは維持（ADR-0007）。本Phaseの対象外
- stale検出は `os.statvfs` timeout ベース（macOS前提、`/proc/mounts` 不要）
- force unmountは `umount -f`

### 実行手順

#### Step 1: subprocess.run に timeout 付与
- [ ] `mount.py:_mount_one` の `subprocess.run` に `timeout=30` を追加
- [ ] `TimeoutExpired` を捕捉し `FAIL: timeout` を返す

#### Step 2: stale マウント検出
- [ ] `health.py:HealthState` に `"stale"` を追加
- [ ] `inspect_mount` で `is_mount()=True` の場合、`os.statvfs` をスレッドで実行し3秒timeout → `"stale"` を返す

#### Step 3: stale マウントの force unmount
- [ ] `mount.py:_unmount_one` で stale 検出時に `umount -f` を実行
- [ ] 通常unmount失敗時のフォールバックとしても `umount -f` を試行

### 受け入れ基準
- `subprocess.run`(sshfs) に timeout が設定されている
- staleマウントを `"stale"` 状態として検出できる
- staleマウントに対して `umount -f` が実行される
- timeout発生時に適切なエラーメッセージが表示される

対象: `commands/mount.py` + `health.py` に閉じた変更。

---

## Phase 3: State/GitInfo接続 + status拡張

元タスク: refactoring Phase 5 + status-dashboard Phase 3-4

### 3A: モデル接続（refactoring Phase 5）
- [ ] State の status/priority を status 表示と編集処理へ接続
- [ ] GitInfo を status の git 状態取得へ接続
- [ ] manifest version を検証するか廃止するか決定
- [ ] doctor の責務定義 → 実装 or CLI登録解除

### 3B: status表示拡張（status-dashboard Phase 3）
- [ ] resource ごとの git 差分ファイル数取得ロジック
- [ ] state.yaml から status text / priority を読み込み表示に統合
- [ ] 表示フォーマット実装（priority emoji, git count, status text）

### 3C: status編集機能（status-dashboard Phase 4）
- [ ] `-e <resource> "text"` で status text を更新
- [ ] `-p <resource> <priority>` で priority を更新
- [ ] manifest との resource 名バリデーション

---

## Phase 4: 回帰テスト整備

元タスク: refactoring Phase 6

- [ ] workspace-hubルート起点の固定manifest・stateパスを検証
- [ ] `.gitignore` と managed block がユーザー記述を失わないテスト
- [ ] `.codex` 配布方式の保持・置換範囲を検証
- [ ] symlink 状態と link/status の整合性テスト
- [ ] shell 終了コード、補完、State/GitInfo連携のCLIテスト

---

## Phase 5: whub todo（独立・任意のタイミングで着手可）

元タスク: whub-task-command

- [ ] `~/.whub/todos.yaml` の Pydantic モデル + load/save
- [ ] curses TUI（Add / Done / Delete / View completed）
- [ ] resource 補完（manifest連携）
- [ ] priority 色分け表示
- [ ] CLI登録（`whub todo`）

---

## Phase 6: init コマンド + mind/recruit整理

元タスク: status-dashboard Phase 5 + mind-recruit-consolidation

- [ ] `whub init` 実装（`.whub/` 生成、shell-init統合）
- [ ] mind をSSOTに、recruit から参照構造へ整理（非コード作業）

---

## コードレビュー指摘事項（Phase横断で対処）

修正済み:
- [x] `commands/cd.py:43` — remote_path を `shlex.quote` で保護
- [x] `models/manifest.py:64` — `resolve_path` に `..` パストラバーサル検証を追加
- [x] `commands/link.py:26` — managed block以降のユーザー記述を保持するよう修正
- [x] `commands/boot.py:82` — hooks を dict マージに変更（プロジェクト固有イベント保持）

未対処（各Phase作業時に対処）:
- [ ] `commands/shell_init.py:16` — eval 注入リスク（Phase 1 Step 2 で os.execvp 化により解消）
- [ ] `models/manifest.py:68` — cwd依存、上方探索なし（Phase 3A で検討）

対処不要:
- [x] `commands/mount.py:50` — sshfs `-s` フラグ：意図的に維持（ADR-0007）
