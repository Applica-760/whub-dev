# whub 残作業（統合）

## 概要

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
