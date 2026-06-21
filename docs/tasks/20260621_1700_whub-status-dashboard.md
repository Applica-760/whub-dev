# whub 基盤整備 + status 拡張

## 目的・前提・方針案

### 目的
1. whub の基盤整備（`.whub/` ディレクトリ導入、init コマンド、models 整理）
2. `whub status` を resource 単位のダッシュボードに拡張

### 前提
- 既存 `status.py`: manifest から resource 一覧を取得し、type + link 状態を表示（非インタラクティブ）
- `whub todo`（別タスク）で管理される `todos.yaml` との連携あり（片方向読み取り）
- CLI は Python（uv + Click + Pydantic + pyyaml）

---

### 決定事項

#### A. `.whub/` ディレクトリ導入
- **配置**: カレントディレクトリ（プロジェクトルート）直下に `.whub/` を作成。`~/` ではない
- `manifest.yaml` を `.whub/` 配下に移動
- 可変状態（status, priority, todos）も `.whub/` 配下に格納

#### B. `whub init` コマンド新設
- `.whub/` ディレクトリ生成 + 初期ファイル配置
- 既存の `whub shell-init` 機能を統合し、より強い初期化コマンドにする

#### C. models 整理
- 現在の `manifest.py` のモデル群を `models/` パッケージに移動
- 各モジュールはモデル定義 + 対応する読み書き操作を同居（manifest.py の既存パターンに統一）
- 構成:
```
src/whub/models/
  __init__.py       # re-exports
  manifest.py       # Host, GitInfo, Resource, Manifest + load_manifest()
  state.py          # ResourceState + load_state() / save_state()
```
- `.whub/` のパス解決は `models/__init__.py` のヘルパーで提供。独立した store モジュールは不要

#### D. status / priority のストレージ
- manifest.yaml とは**分離**。理由: manifest はインフラ定義（不変）、status/priority は可変状態。pyyaml で manifest を書き戻すとコメントが消える
- 可変状態は `.whub/state.yaml`（仮称）に格納
- resource 名は manifest からバリデーション（存在しない resource への書き込みを防止）
- ファイル不在時は空として扱う（自動生成しない）

```yaml
# .whub/state.yaml
resources:
  esn-lab:
    status: "採食/反芻で訓練中"
    priority: "red"
  la-imitation:
    status: "シミュで箱掴む"
    priority: "yellow"
```

#### E. `whub status` 表示仕様
- **表示のみ**。TUI / インタラクティブ操作なし
- 表示項目: priority, resource name, type, link status, git 差分ファイル数, status text, todo 数
- todo 数: `todos.yaml`（別タスクで実装）が存在しない場合は列自体を非表示

```
$ whub status

  Resource           Type      Link        Git   Status
  ──────────────────────────────────────────────────────────
  🔴 esn-lab         mount     mounted      3    採食/反芻で訓練中
  🟡 la-imitation    mount     mounted      0    シミュで箱掴む
     portfolio        symlink   ok           1    ──
  🔵 recruit         symlink   ok           0    自分史を書く
```

#### F. status / priority 編集
- CLIオプションで編集。TUI不要
```bash
whub status -e <resource> "ステータス記述"    # status text 編集
whub status -p <resource> red                 # priority 編集 (red/yellow/blue/none)
```

---

### 検討中

1. **manifest バリデーションタイミング**: state.yaml 読み込み時に manifest と突合するか、書き込み時のみか。実装時に判断
2. **`whub init` の詳細仕様**: shell-init との統合方法、manifest skeleton 生成の有無。init 実装時に設計

---

### 非機能要件
1. AI 非依存 — CLI コマンドのみで完結
2. 既存の `whub` コマンド体系（Click group）に統合
3. 新規依存は最小限（pyyaml 既存、ruamel.yaml は不要になった）

---

## 計画

### Phase 1: models/ パッケージ整理
- [ ] `src/whub/models/` 作成、`manifest.py` のモデル定義 + `load_manifest()` を移動
- [ ] `models/__init__.py` に `.whub/` パス解決ヘルパー + re-exports
- [ ] `src/whub/models/state.py` に `ResourceState` モデル + `load_state()` / `save_state()` 定義
- [ ] 既存 import を全コマンドで更新・動作確認

### Phase 2: `.whub/` + manifest 移動
- [ ] `manifest.yaml` を `.whub/` 配下に移動
- [ ] `load_manifest` のデフォルトパスを `.whub/manifest.yaml` に変更
- [ ] 既存コマンドの動作確認

### Phase 3: `whub status` 表示拡張
- [ ] resource ごとの git 差分ファイル数取得ロジック
- [ ] state.yaml から status text / priority を読み込み表示に統合
- [ ] 表示フォーマット実装（priority emoji, git count, status text）

### Phase 4: `whub status -e / -p` 編集機能
- [ ] `-e <resource> "text"` で state.yaml の status text を更新
- [ ] `-p <resource> <priority>` で state.yaml の priority を更新
- [ ] manifest との resource 名バリデーション

### Phase 5: `whub init` コマンド（検討中の仕様を確定してから）
- [ ] `whub init` 実装（`.whub/` 生成、shell-init 統合）

## 実行ログ

（実装開始後に記録）

## 結果

（完了後に記録）
