# Boot 配布（.my-boot 統合）

## 目的・前提・方針案

- ロードマップ Phase 6（Agent ルール配布）を前倒しし、`.my-boot/install.sh` の役割を `whub boot deploy` に統合する
- .my-boot は独立リポとして維持し、workspace-hub から symlink 経由でテンプレートソースとして参照する
- ADR-0006 の方針を一部変更（下記）
- boot.py にロジックを集約し、cli.py は薄く保つ

### ADR-0006 からの変更点

| 項目 | 旧（ADR-0006） | 新 |
|------|----------------|-----|
| CLAUDE.md | テンプレートが親、プロジェクト固有をマーカー外に配置 | **既存 CLAUDE.md を尊重し、冒頭にマーカー付き共通セクションを挿入** |
| AGENTS.md | 上書き | **CLAUDE.md と同じマーカー方式** |
| settings.json hooks | 上書き | 上書き（変更なし） |
| install.sh | `whub boot deploy` で廃止 | **install.sh は現行維持（スタンドアロン用）、whub は独自実装** |

### 配布戦略（確定）

install.sh の構造を反映:

| ソース（.my-boot 内） | 配布先 | 戦略 |
|----------------------|--------|------|
| `claude/` → `.claude/`（mcp.json 除外） | CLAUDE.md はマーカー、settings.json はマージ、skills 等は上書き | |
| `claude/mcp.json` → `.mcp.json` | 上書き | |
| `codex/` → `.codex/` | 上書き | |
| `codex/AGENTS.md` → `AGENTS.md` | マーカー | |

### 対象リソース

- `manifest.yaml` で `boot: true` かつ `type: symlink` のリソース + workspace-hub 自身

### .my-boot クリーンアップ

whub 直下で開発するため、.my-boot 内の自己開発用ファイルは不要:

| 削除対象 | 由来 |
|----------|------|
| `.claude/` | `claude/` のコピー（install.sh 自身で生成） |
| `.codex/` | `codex/` のコピー |
| `AGENTS.md` | `codex/AGENTS.md` への symlink |

テンプレートソースの `claude/`, `codex/` は維持。

## 計画

### Phase 1: .my-boot テンプレート整備
- [x] Step 1: CLAUDE.md にマーカー追加（`<!-- hub:managed:start -->` / `<!-- hub:managed:end -->`）
- [x] Step 2: AGENTS.md にマーカー追加（同上）
- [x] Step 3: `rules` → `boot` にコマンド名変更（cli.py, ADR-0005/0006, cli-commands.yaml, タスクドキュメント）
- [x] Step 4: `agent_rules` → `boot` にフラグ名変更（manifest.yaml, manifest.py, ADR-0004, 全参照ドキュメント）

### Phase 2: .my-boot クリーンアップ
- [x] Step 1: .my-boot から `.claude/`, `.codex/`, `AGENTS.md`（symlink）を削除

### Phase 3: `whub boot deploy` 実装
- [x] Step 1: `src/whub/boot.py` — install.sh 等価の配布ロジック（マーカー挿入 + settings マージ + コピー + .gitignore更新）
- [x] Step 2: `cli.py` の `boot_deploy` — `deploy_all(manifest)` を呼ぶだけの薄いラッパー

### Phase 4: `whub doctor` マーカー検証
- [ ] Step 1: 対象リソースの CLAUDE.md / AGENTS.md でマーカーの存在・整合性チェック

### Phase 5: ADR-0006 更新
- [ ] Step 1: 変更点（マーカー挿入方式、AGENTS.md マーカー化、install.sh 維持）を反映

### Phase 6: 動作検証
- [ ] Step 1: `whub boot deploy` を実行し、symlink 先プロジェクトへの配布を確認
- [ ] Step 2: workspace-hub 自身への配布を確認
- [ ] Step 3: 既存 CLAUDE.md があるプロジェクト / 無いプロジェクト両方で検証
- [ ] Step 4: 2回目の deploy で冪等性を確認

## 実行ログ

（なし）

## 結果

（未完了）
