# whub 残作業（統合）

## 概要

status拡張は [20260622_1830_whub-status-enhancement.md](20260622_1830_whub-status-enhancement.md) に移動。

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
